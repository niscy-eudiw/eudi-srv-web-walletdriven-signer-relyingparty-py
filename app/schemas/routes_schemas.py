class SigningOptions:
    filename: str
    container: str
    signature_format: str
    packaging: str
    level: str

    def __init__(self, filename: str, container: str, signature_format: str, packaging: str, level: str):
        self.filename = self._filename_validator(filename)
        self.container = container
        self.signature_format = signature_format
        self.packaging = packaging
        self.level = level

    @staticmethod
    def _filename_validator(value: str) -> str:
        if "/" in value or "\\" in value or value.startswith("."):
            raise ValueError("Invalid filename")
        return value

class WalletOptions:
    VALID_PROTOCOL_VERSIONS = {"etsi119432", "previous"}
    VALID_REQUEST_OBJECT_DELIVERY = {"request_uri", "link"}

    VALID_DELIVERY_METHODS = {"redirect", "request"}
    VALID_AUTHORIZATION_ENDPOINTS = {"eudi-rqes://", "mdoc-openid4vp://"}

    protocol_version: str
    request_object_delivery: str | None
    wallet_delivery_method: str
    authorization_endpoint: str | None

    def __init__(self, wallet_delivery_method: str, authorization_endpoint: str, protocol_version: str, request_object_delivery: str):
        self.protocol_version = self._validate_choice(
            protocol_version, self.VALID_PROTOCOL_VERSIONS, "protocol_version"
        )
        if self.protocol_version == "etsi119432":
            if not request_object_delivery:
                raise ValueError("request_object_delivery is required when protocol_version is 'ETSI 119 432 v1.3.1'")
            self.request_object_delivery = self._validate_choice(
                request_object_delivery, self.VALID_REQUEST_OBJECT_DELIVERY, "request_object_delivery"
            )
        else:
            self.request_object_delivery = None

        self.wallet_delivery_method = self._validate_choice(
            wallet_delivery_method, self.VALID_DELIVERY_METHODS, "wallet_delivery_method")
        if self.wallet_delivery_method == "redirect":
            if not authorization_endpoint:
                raise ValueError("authorization_endpoint is required when wallet_delivery_method is 'redirect'")
            self.authorization_endpoint = self._validate_choice(
                authorization_endpoint, self.VALID_AUTHORIZATION_ENDPOINTS, "authorization_endpoint"
            )
        else:
            self.authorization_endpoint = None



    @staticmethod
    def _validate_choice(value: str, allowed: set, field_name: str) -> str:
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(f"Invalid {field_name}: {value!r}")
        return value

    @classmethod
    def from_form(cls, form) -> "WalletOptions":
        return cls(
            wallet_delivery_method = form.get("wallet_delivery_method"),
            authorization_endpoint = form.get("authorization_endpoint"),
            protocol_version = form.get("protocol_version"),
            request_object_delivery = form.get("request_object_delivery"),
        )