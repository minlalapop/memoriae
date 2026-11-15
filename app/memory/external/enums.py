import enum


class StatutVerification(str, enum.Enum):
    DECLARE = "declare"
    NON_VERIFIE = "non_verifie"
    VERIFIE = "verifie"


class ProvenanceSouvenir(str, enum.Enum):
    PATIENT = "patient"
    PROCHE = "proche"
    PROFESSIONNEL = "professionnel"
    DOCUMENT = "document"
    AUTRE = "autre"


class TypeElement(str, enum.Enum):
    TEXTE = "texte"
    IMAGE = "image"


class FeedbackRecuperation(str, enum.Enum):
    RETROUVE = "retrouve"
    NON_RETROUVE = "non_retrouve"
    PARTIEL = "partiel"
    DEMANDE_AIDE = "demande_aide"


class ResultatRecuperation(str, enum.Enum):
    RETROUVE = "retrouve"
    NON_RETROUVE = "non_retrouve"
    ASSISTANCE_EXTERNE = "assistance_externe"
    ABANDON = "abandon"
