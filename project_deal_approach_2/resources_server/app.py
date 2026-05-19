"""Approach 2 Resources Server.

Exposes a SINGLE endpoint /run_marketplace that runs the full 10-agent
simulation inside one request. NeMo Gym fires one tool call per task and
waits for the result.

This module exposes:
  - build_app() -> FastAPI: pure FastAPI app (used in tests).
  - MarketplaceServer: NeMo Gym SimpleResourcesServer subclass (used in prod).
    The NeMo Gym subclass and `verify()` method are implemented in Task 12b
    once verifiers.py is ready (see verifiers stack in Tasks 13-17).
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from marketplace import config
from marketplace.build_agents import build_agent_prompts
from marketplace.channel import Channel
from marketplace.ledger import Ledger
from marketplace.scheduler import run_marketplace_loop, RunResult

from .gains import compute_per_agent_gains
from .model_config import assign_models, VALID_CONFIGS
from .persona_loader import load_persona_set


class RunMarketplaceRequest(BaseModel):
    persona_set: str
    model_config_name: str = Field(alias="model_config")
    seed: int

    model_config = {"populate_by_name": True}


class RunMarketplaceResponse(BaseModel):
    deals: list[dict]
    channel_log: list[dict]
    per_agent_gains: dict[str, float]
    turns_used: int
    stop_reason: str
    model_assignments: dict[str, str]


def _run_simulation(persona_set: str, model_config_name: str, seed: int) -> RunMarketplaceResponse:
    if model_config_name not in VALID_CONFIGS:
        raise HTTPException(status_code=400, detail=f"invalid model_config: {model_config_name}")

    personas = load_persona_set(persona_set)
    models_by_agent = assign_models(personas, model_config_name)
    agent_prompts = build_agent_prompts(personas)

    # Each call writes to a unique temp file so concurrent rollouts don't clobber.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    tmp_root = Path(config.DATA_DIR) / "tmp_runs" / f"{persona_set}_{model_config_name}_seed{seed}_{stamp}"
    tmp_root.mkdir(parents=True, exist_ok=True)

    channel = Channel(path=tmp_root / "channel.jsonl")
    channel.clear()
    ledger = Ledger(path=tmp_root / "deals.json")
    ledger.clear()

    result: RunResult = run_marketplace_loop(
        personas=personas,
        agent_prompts=agent_prompts,
        models_by_agent=models_by_agent,
        channel=channel,
        ledger=ledger,
        seed=seed,
    )

    gains = compute_per_agent_gains(personas, ledger.deals)

    deals_json = [
        {
            "deal_id": d.deal_id, "seller": d.seller, "buyer": d.buyer,
            "item_id": d.item_id, "item_name": d.item_name,
            "price": d.price, "seller_floor": d.seller_floor,
            "buyer_ceiling": d.buyer_ceiling, "turn": d.turn,
        }
        for d in ledger.deals
    ]
    channel_json = [
        {
            "turn": e.turn, "event_id": e.event_id, "agent": e.agent,
            "action": e.action, "target": e.target, "price": e.price,
            "message": e.message, "timestamp": e.timestamp,
        }
        for e in channel.events
    ]

    return RunMarketplaceResponse(
        deals=deals_json,
        channel_log=channel_json,
        per_agent_gains=gains,
        turns_used=result.turns_used,
        stop_reason=result.stop_reason,
        model_assignments=models_by_agent,
    )


def build_app() -> FastAPI:
    """Build a plain FastAPI app exposing /run_marketplace (used in tests + smoke runs)."""
    app = FastAPI(title="Approach 2 Marketplace Resources Server")

    @app.post("/run_marketplace", response_model=RunMarketplaceResponse)
    def run_marketplace(req: RunMarketplaceRequest) -> RunMarketplaceResponse:
        return _run_simulation(req.persona_set, req.model_config_name, req.seed)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = build_app()


# ---- NeMo Gym integration ------------------------------------------------

try:
    from nemo_gym.base_resources_server import (
        SimpleResourcesServer, BaseVerifyRequest, BaseVerifyResponse,
    )
    _NEMO_GYM_AVAILABLE = True
except Exception:
    _NEMO_GYM_AVAILABLE = False
    SimpleResourcesServer = object  # type: ignore
    BaseVerifyRequest = object  # type: ignore
    BaseVerifyResponse = object  # type: ignore


from .verifiers import compute_rubric_scores


class MarketplaceServer(SimpleResourcesServer):  # type: ignore[misc]
    """NeMo Gym Resources Server for Approach 2 marketplace simulation."""

    JUDGE_MODEL: ClassVar[str] = "openai/gpt-4o-2024-11-20"

    if _NEMO_GYM_AVAILABLE:
        # Allow MarketplaceServer() construction in tests without requiring the
        # full NeMo Gym BaseResourcesServerConfig + ServerClient (NeMo Gym only
        # supplies those when ng_run boots the server).
        model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

        def __init__(self, **data):
            if "config" not in data:
                data["config"] = None
            if "server_client" not in data:
                data["server_client"] = None
            try:
                super().__init__(**data)
            except Exception:
                # Fall back to BaseModel.__init__ bypass for test-only instantiation.
                object.__setattr__(self, "__dict__", {**data})

    def setup_webserver(self) -> FastAPI:  # type: ignore[override]
        if _NEMO_GYM_AVAILABLE:
            app = super().setup_webserver()
        else:
            app = FastAPI(title="Approach 2 Marketplace Resources Server (no NeMo Gym)")

        @app.post("/run_marketplace", response_model=RunMarketplaceResponse)
        def run_marketplace(req: RunMarketplaceRequest) -> RunMarketplaceResponse:
            return _run_simulation(req.persona_set, req.model_config_name, req.seed)

        @app.get("/healthz")
        def healthz():
            return {"ok": True}

        return app

    def verify_inline(
        self,
        run_result: dict,
        persona_set: str,
        model_config_name: str,
        seed: int,
        expected_possible_deals: int,
    ) -> dict:
        """Run verification given an already-completed run_result. Test-friendly."""
        personas = load_persona_set(persona_set)
        scores = compute_rubric_scores(
            run_result=run_result,
            personas=personas,
            model_config_name=model_config_name,
            expected_possible_deals=expected_possible_deals,
            judge_model=self.JUDGE_MODEL,
        )
        return {"reward": scores["final_reward"], "rubric_scores": scores}

    async def verify(self, body) -> dict:  # NeMo Gym signature
        """Parse the rollout response, extract the run_marketplace tool result,
        and compute the rubric scores. Called once per rollout by NeMo Gym."""
        metadata = getattr(body, "metadata", {}) or {}
        persona_set = metadata.get("persona_set")
        model_config_name = metadata.get("model_config")
        seed = metadata.get("seed", 0)
        expected_possible_deals = metadata.get("expected_possible_deals", 8)

        run_result = _extract_tool_result(body)

        out = self.verify_inline(
            run_result=run_result,
            persona_set=persona_set,
            model_config_name=model_config_name,
            seed=seed,
            expected_possible_deals=expected_possible_deals,
        )
        # Build a BaseVerifyResponse-compatible dict (NeMo Gym handles the schema).
        if _NEMO_GYM_AVAILABLE:
            return BaseVerifyResponse(
                **(body.model_dump() if hasattr(body, "model_dump") else {}),
                reward=out["reward"],
                **{"rubric_scores": out["rubric_scores"]},
            )
        return out


def _extract_tool_result(body) -> dict:
    """Pull the run_marketplace tool-call result out of a rollout response.

    NeMo Gym's `body.response` is expected to contain a tool call output for
    `run_marketplace`. The exact path depends on NeMo Gym's schema — we look
    in a few common locations and fall back to body.run_result if present.
    """
    if hasattr(body, "run_result") and isinstance(body.run_result, dict):
        return body.run_result
    response = getattr(body, "response", None)
    if isinstance(response, dict):
        for key in ("tool_result", "result", "output"):
            if key in response and isinstance(response[key], dict):
                return response[key]
        return response
    if isinstance(response, list):
        for item in response:
            if isinstance(item, dict) and "deals" in item:
                return item
    raise ValueError("could not extract run_marketplace tool result from body")
