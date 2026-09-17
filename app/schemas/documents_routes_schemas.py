from typing import Optional, Literal
from pydantic import BaseModel, field_validator, model_validator

class SigningOptions(BaseModel):
    filename: str
    container: Literal["No", "ASiC-S", "ASiC-E"]
    signature_format: Literal["X", "P", "C", "J"]
    packaging: Literal["ENVELOPED", "ENVELOPING", "DETACHED", "INTERNALLY_DETACHED"]
    level: Literal["Ades-B-B", "Ades-B-T", "Ades-B-LT", "Ades-B-LTA"]

    @field_validator("filename")
    @classmethod
    def _filename_validator(cls, value: str) -> str:
        if "/" in value or "\\" in value or value.startswith("."):
            raise ValueError("Invalid filename")
        return value

class WalletOptions(BaseModel):
    protocol_version: Literal["etsi119432", "previous"]
    request_object_delivery: Optional[Literal["request_uri", "link"]]
    wallet_delivery_method: Literal["redirect", "request"]
    authorization_endpoint: Optional[Literal["eudi-rqes://", "mdoc-openid4vp://"]]

    @model_validator(mode="after")
    def check_conditional_requirements(self)->"WalletOptions":
        if self.protocol_version == "etsi119432" and not self.request_object_delivery:
            raise ValueError("request_object_delivery is required when protocol_version is 'etsi119432'")
        if self.wallet_delivery_method == "redirect" and not self.authorization_endpoint:
            raise ValueError("authorization_endpoint is required when wallet_delivery_method is 'redirect'")
        return self

    @classmethod
    def from_form(cls, form) -> "WalletOptions":
        return cls.model_validate(dict(form))