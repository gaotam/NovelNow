from consts import ProviderName
from providers.goctruyentranhvui import GocTruyenTranhVuiProvider
from providers.metruyenchu import MeChuyenChuProvider
from providers.truyenqqto import TruyenQQTOProvider

PROVIDER_MAP = {
    ProviderName.TRUYENQQTO.value: TruyenQQTOProvider,
    ProviderName.METRUYENCHU.value: MeChuyenChuProvider,
    ProviderName.GOCTRUYENTRANHVUI.value: GocTruyenTranhVuiProvider
}