"""Request and response models for the public API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

N_FEATURES = 64
PIXEL_MIN = 0.0
PIXEL_MAX = 16.0

Pixel = Annotated[float, Field(ge=PIXEL_MIN, le=PIXEL_MAX, allow_inf_nan=False)]
Image = Annotated[list[Pixel], Field(min_length=N_FEATURES, max_length=N_FEATURES)]


class PredictRequest(BaseModel):
    """A batch of flattened 8x8 grey-scale digit images (pixel values 0-16)."""

    model_config = ConfigDict(extra="forbid")

    instances: Annotated[list[Image], Field(min_length=1)]


class Prediction(BaseModel):
    label: int
    probability: float


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[Prediction]


class HealthResponse(BaseModel):
    status: str
