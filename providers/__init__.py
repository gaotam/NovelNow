from consts import ProviderName
from providers.metruyenchu import MeChuyenChuProvider
from providers.truyenqqto import TruyenQQTOProvider

PROVIDER_MAP = {
    ProviderName.TRUYENQQTO.value: TruyenQQTOProvider,
    ProviderName.METRUYENCHU.value: MeChuyenChuProvider
}