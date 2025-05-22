from consts import ProviderName
from providers.goctruyentranhvui import GocTruyenTranhVuiProvider
from providers.metruyenchu import MeChuyenChuProvider
from providers.nettruyen import NetTruyenProvider
from providers.truyenqqto import TruyenQQTOProvider

PROVIDER_MAP = {
    ProviderName.NETTRUYEN.value: NetTruyenProvider,
    ProviderName.TRUYENQQTO.value: TruyenQQTOProvider,
    ProviderName.METRUYENCHU.value: MeChuyenChuProvider,
    ProviderName.GOCTRUYENTRANHVUI.value: GocTruyenTranhVuiProvider
}