from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from apps.core.choices import DocumentDataType, DocumentLengthType


@deconstructible
class FileValidator:
    """
    Validador de archivos para verificar el tipo MIME y el tamaño máximo.
    """

    def __init__(self, max_size=None, allowed_mimetypes=None):
        self.max_size = max_size
        self.allowed_mimetypes = allowed_mimetypes

    def __call__(self, value):
        if self.max_size is not None and value.size > self.max_size:
            raise ValidationError(
                _(
                    "El tamaño del archivo (%(size)s) excede el tamaño máximo permitido de %(max_size)s."
                ),
                code="file_size",
                params={
                    "size": filesizeformat(value.size),
                    "max_size": filesizeformat(self.max_size),
                },
            )

        if self.allowed_mimetypes and hasattr(value, "content_type"):
            if value.content_type not in self.allowed_mimetypes:
                raise ValidationError(
                    _(
                        "Tipo de archivo no permitido. Tipos permitidos: %(allowed_mimetypes)s."
                    ),
                    code="file_type",
                    params={
                        "allowed_mimetypes": ", ".join(self.allowed_mimetypes)
                    },
                )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.max_size == other.max_size
            and self.allowed_mimetypes == other.allowed_mimetypes
        )


@deconstructible
class CodeValidator:
    """
    Validador genérico para códigos con reglas específicas.
    """

    def __init__(
        self,
        uppercase=False,
        exact_length=None,
        min_length=None,
        max_length=None,
        alphanumeric_only=False,
        numeric_only=False,
        alphabetic_only=False,
        error_message=None,
    ):
        self.uppercase = uppercase
        self.exact_length = exact_length
        self.min_length = min_length
        self.max_length = max_length
        self.alphanumeric_only = alphanumeric_only
        self.numeric_only = numeric_only
        self.alphabetic_only = alphabetic_only
        self.error_message = error_message

    def __call__(self, value):
        if self.uppercase and value != value.upper():
            raise ValidationError(
                self.error_message or _("Code must be in uppercase."),
                code="invalid_case",
            )

        if self.numeric_only and not value.isdigit():
            raise ValidationError(
                self.error_message or _("Code must contain only digits."),
                code="invalid_numeric",
            )

        if self.alphabetic_only and not value.isalpha():
            raise ValidationError(
                self.error_message or _("Code must contain only letters."),
                code="invalid_alphabetic",
            )

        if self.alphanumeric_only and not value.isalnum():
            raise ValidationError(
                self.error_message
                or _("Code must contain only alphanumeric characters."),
                code="invalid_alphanumeric",
            )

        length = len(value)

        if self.exact_length is not None and length != self.exact_length:
            raise ValidationError(
                self.error_message
                or _("Code must be exactly %(length)d characters."),
                params={"length": self.exact_length},
                code="invalid_length",
            )

        if self.min_length is not None and length < self.min_length:
            raise ValidationError(
                self.error_message
                or _("Code must be at least %(length)d characters."),
                params={"length": self.min_length},
                code="invalid_min_length",
            )

        if self.max_length is not None and length > self.max_length:
            raise ValidationError(
                self.error_message
                or _("Code must be at most %(length)d characters."),
                params={"length": self.max_length},
                code="invalid_max_length",
            )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.uppercase == other.uppercase
            and self.exact_length == other.exact_length
            and self.min_length == other.min_length
            and self.max_length == other.max_length
            and self.alphanumeric_only == other.alphanumeric_only
            and self.numeric_only == other.numeric_only
            and self.alphabetic_only == other.alphabetic_only
        )


@deconstructible
class DocumentNumberValidator:
    """
    Validador de números de documento según el tipo de documento.
    """

    def __init__(self, document_type=None):
        self.document_type = document_type

    def __call__(self, value):
        if not self.document_type:
            return

        if (
            self.document_type.data_type == DocumentDataType.NUMERIC
            and not value.isdigit()
        ):
            raise ValidationError(
                _("Document number must contain only digits."),
                code="invalid_numeric",
            )

        if (
            self.document_type.data_type == DocumentDataType.ALPHANUMERIC
            and not value.isalnum()
        ):
            raise ValidationError(
                _("Document number must contain only alphanumeric characters."),
                code="invalid_alphanumeric",
            )

        doc_len = len(value)

        if (
            self.document_type.length_type == DocumentLengthType.EXACT
            and doc_len != self.document_type.length
        ):
            raise ValidationError(
                _("Document number must have exactly %(length)d characters."),
                params={"length": self.document_type.length},
                code="invalid_length_exact",
            )

        if (
            self.document_type.length_type == DocumentLengthType.MAXIMUM
            and doc_len > self.document_type.length
        ):
            raise ValidationError(
                _(
                    "Document number must have a maximum of %(length)d characters."
                ),
                params={"length": self.document_type.length},
                code="invalid_length_max",
            )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.document_type == other.document_type
        )


@deconstructible
class GeographicRelationValidator:
    """
    Validador para relaciones geográficas jerárquicas.
    """

    def __init__(self, parent_field, child_field, error_message=None):
        self.parent_field = parent_field
        self.child_field = child_field
        self.error_message = error_message

    def __call__(self, instance):
        parent = getattr(instance, self.parent_field, None)
        child = getattr(instance, self.child_field, None)

        if parent and child:
            child_parent = getattr(child, self.parent_field, None)
            if child_parent != parent:
                raise ValidationError(
                    {
                        self.child_field: self.error_message
                        or _(
                            f"The selected {self.child_field} does not belong to the chosen {self.parent_field}."
                        )
                    }
                )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.parent_field == other.parent_field
            and self.child_field == other.child_field
        )


@deconstructible
class PhoneNumberValidator:
    """
    Validador para números de teléfono con soporte para diferentes formatos.
    """

    def __init__(
        self,
        allow_international=False,
        require_mobile=False,
        country_code="+51",  # Default to Peru
        min_digits=7,
        max_digits=15,
    ):
        self.allow_international = allow_international
        self.require_mobile = require_mobile
        self.country_code = country_code
        self.min_digits = min_digits
        self.max_digits = max_digits

    def __call__(self, value):
        if not value:
            return

        cleaned = (
            value.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if cleaned.startswith("+"):
            if not self.allow_international:
                raise ValidationError(
                    _("International phone numbers are not allowed."),
                    code="international_not_allowed",
                )
            cleaned = cleaned[1:]

        if not cleaned.isdigit():
            raise ValidationError(
                _("Phone number must contain only digits."),
                code="invalid_characters",
            )

        if len(cleaned) < self.min_digits:
            raise ValidationError(
                _("Phone number must have at least %(min)d digits."),
                params={"min": self.min_digits},
                code="too_short",
            )

        if len(cleaned) > self.max_digits:
            raise ValidationError(
                _("Phone number must have at most %(max)d digits."),
                params={"max": self.max_digits},
                code="too_long",
            )

        if self.require_mobile and self.country_code == "+51":
            if not cleaned.startswith("9") or len(cleaned) != 9:
                raise ValidationError(
                    _(
                        "Must be a valid mobile number (9 digits starting with 9)."
                    ),
                    code="invalid_mobile",
                )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.allow_international == other.allow_international
            and self.require_mobile == other.require_mobile
            and self.country_code == other.country_code
        )


image_validator = FileValidator(
    max_size=500 * 1024,  # 500 KB
    allowed_mimetypes=[
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ],
)

document_validator = FileValidator(
    max_size=5 * 1024 * 1024,  # 5 MB
    allowed_mimetypes=[
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
)

uppercase_code_validator = CodeValidator(
    uppercase=True, error_message=_("Code must be in uppercase.")
)

currency_code_validator = CodeValidator(
    uppercase=True,
    alphabetic_only=True,
    exact_length=3,
    error_message=_("Currency code must be exactly 3 uppercase letters."),
)

document_type_code_validator = CodeValidator(
    numeric_only=True,
    exact_length=2,
    error_message=_("Document type code must be exactly 2 digits."),
)

province_department_validator = GeographicRelationValidator(
    parent_field="department",
    child_field="province",
    error_message=_(
        "The selected province does not belong to the chosen department."
    ),
)

district_province_validator = GeographicRelationValidator(
    parent_field="province",
    child_field="district",
    error_message=_(
        "The selected district does not belong to the chosen province."
    ),
)


def validate_uppercase_code(value):
    """Función helper para validación simple de uppercase."""
    uppercase_code_validator(value)


def validate_currency_code(value):
    """Función helper para validación de código de moneda."""
    currency_code_validator(value)


def validate_document_code(value):
    """Función helper para validación de código de documento."""
    document_type_code_validator(value)


def validate_document_by_type(document_number: str, document_type) -> None:
    """
    Función helper para validar un documento con su tipo.
    Útil cuando el tipo no está disponible en tiempo de definición del modelo.
    """
    validator = DocumentNumberValidator(document_type)
    validator(document_number)


def validate_province_in_department(province, department):
    """
    Función helper para validar relación provincia-departamento.
    Útil para validaciones en formularios o vistas.
    """
    if province and department and province.department != department:
        raise ValidationError(
            {
                "province": _(
                    "The selected province does not belong to the chosen department."
                )
            }
        )


def validate_district_in_province(district, province):
    """
    Función helper para validar relación distrito-provincia.
    Útil para validaciones en formularios o vistas.
    """
    if district and province and district.province != province:
        raise ValidationError(
            {
                "district": _(
                    "The selected district does not belong to the chosen province."
                )
            }
        )
