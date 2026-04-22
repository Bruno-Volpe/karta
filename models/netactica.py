from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class SessionRequest(BaseModel):
    UserName: str
    Password: str
    UserService: str


class TokenData(BaseModel):
    TokenId: str


class SessionResponse(BaseModel):
    Token: TokenData


# ---------------------------------------------------------------------------
# Autocomplete / Location
# ---------------------------------------------------------------------------

class AutocompleteLocation(BaseModel):
    Id: int
    Type: str
    nearestIataCode: Optional[str] = None
    Name: str
    AsciiName: Optional[str] = None
    NameFull: Optional[str] = None


class AutocompleteResponse(BaseModel):
    locations: list[AutocompleteLocation] = []
    Hotels: list[dict] = []


# ---------------------------------------------------------------------------
# Hotel Search (HotelSearchV3)
# ---------------------------------------------------------------------------

class SearchRoom(BaseModel):
    """Room occupancy for the search request."""
    Adults: int
    Children: int = 0
    ChildrenAges: list[int] = []


class RequestSettings(BaseModel):
    Language: str = "en"
    ClientId: Optional[str] = None
    SalesChannelCode: Optional[str] = None
    BusinessUnitCode: Optional[str] = None
    SaleType: Optional[str] = None
    BranchCode: Optional[str] = None
    PromoCode: Optional[str] = None
    Platform: Optional[str] = None


class HotelSearchRequest(BaseModel):
    DestinationType: str = "location"
    LocationId: int
    CheckIn: str   # "YYYY-MM-DD"
    CheckOut: str  # "YYYY-MM-DD"
    Rooms: list[SearchRoom]
    SessionToken: str
    IncludeHotelInfo: bool = True
    IncludeRooms: bool = True
    IncludeAlternativeCurrencies: bool = False
    NotFilterHotelsWithoutCompleteStaticInformation: bool = False
    MaxResults: int = 50
    RequestSettings: Optional[RequestSettings] = None


class HotelSearchResponse(BaseModel):
    SearchId: str
    ResultsCount: int
    ResultsAvailableUntil: Optional[str] = None
    Results: list[dict] = []


# ---------------------------------------------------------------------------
# Hotel Results (HotelResultsV2)
# ---------------------------------------------------------------------------

class HotelResultsRequest(BaseModel):
    SearchId: str
    SessionToken: str
    IncludeRooms: bool = True
    IncludeAlternativeCurrencies: bool = False
    OrderCriteria: str = "RECOMENDATION"
    OrderDesc: bool = False
    # Filters
    Categories: list[str] = []      # strings: ["4", "5"]
    Score: Optional[float] = None
    RefundableType: Optional[int] = None  # 0=Refundable, 1=NonRefundable
    Boards: list[str] = []
    Tags: list[str] = []
    Ammenities: list[str] = []
    Zones: list[str] = []
    PropertyTypes: list[str] = []
    Providers: list[str] = []
    PriceFrom: Optional[float] = None
    PriceTo: Optional[float] = None
    HotelName: Optional[str] = None
    Chains: list[str] = []
    ResultCountLowerBound: Optional[int] = None
    ResultCountUpperBound: int = 20  # obrigatório >= 1 na API


class Price(BaseModel):
    Amount: Optional[float] = None
    Fees: Optional[float] = None
    Taxes: Optional[float] = None
    VAT: Optional[float] = None
    DiscountAmount: Optional[float] = None
    TotalDiscount: Optional[float] = None
    TotalDiscountPercentage: Optional[float] = None
    CommissionAmount: Optional[float] = None
    CommissionPercentage: Optional[float] = None
    Strikethrough: Optional[float] = None
    Total: Optional[float] = None
    CurrencyCode: Optional[str] = None


class RoomRate(BaseModel):
    """Sibling of Rooms[] in the hotel result — NOT nested inside a Room."""
    Cost: Optional[Price] = None
    Price: Optional[Price] = None
    # 0 = Refundable, 1 = NonRefundable (inverted!)
    RefundableType: Optional[int] = None
    RefundableInfo: Optional[str] = None
    RoomIds: list[Any] = []
    # RateId can be a simple string "1" or a complex array
    RateId: Optional[Any] = None
    TextFare: Optional[str] = None
    PayAtDestination: bool = False
    RequiredGuarantee: bool = False
    RateType: Optional[str] = None

    @property
    def is_refundable(self) -> bool:
        """API is inverted: 0 = Refundable, 1 = NonRefundable."""
        return self.RefundableType == 0


class HotelRoom(BaseModel):
    RoomId: Optional[Any] = None
    RoomCode: Optional[str] = None
    Description: Optional[str] = None
    Adults: Optional[int] = None
    Children: Optional[int] = None
    BoardCode: Optional[str] = None
    BoardDescription: Optional[str] = None
    BoardTypeCode: Optional[str] = None
    RefundableType: Optional[int] = None
    PromotionalText: Optional[str] = None
    ParsedPromotionalText: Optional[str] = None
    Amenities: list[str] = []
    Images: list[Any] = []
    QuantityRoomImages: Optional[int] = None


class HotelResult(BaseModel):
    HotelName: Optional[str] = None
    HotelCode: Optional[str] = None
    HotelId: Optional[int] = None
    PropertyTypes: Optional[Any] = None  # API returns str ("Hotels"), not list
    ShortDescription: Optional[str] = None
    Destination: Optional[str] = None
    Category: Optional[int] = None   # API returns int (2, 4, 5), not str
    FullAddress: Optional[str] = None
    Images: list[Any] = []
    Zone: Optional[str] = None
    Chain: Optional[str] = None
    Amenities: list[str] = []
    OptionId: Optional[Any] = None
    PriceFrom: Optional[float] = None  # API returns float, not Price object
    RoomName: Optional[str] = None
    BoardTypeCode: Optional[str] = None
    Rooms: list[HotelRoom] = []
    RoomRates: list[RoomRate] = []   # sibling of Rooms, NOT nested
    Score: Optional[float] = None
    ScoreReview: Optional[str] = None
    ExcludesVAT: Optional[bool] = None


# ---------------------------------------------------------------------------
# Hotel Details (static content)
# ---------------------------------------------------------------------------

class HotelImage(BaseModel):
    """Static Content API returns lowercase/snake_case fields."""
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class HotelRating(BaseModel):
    Score: Optional[float] = None
    ScoreOutOf: Optional[float] = None
    ScoreDescription: Optional[str] = None


class HotelMetaReview(BaseModel):
    CategoryName: Optional[str] = None
    Text: Optional[str] = None
    ShortText: Optional[str] = None
    Score: Optional[float] = None
    EvaluationCount: Optional[int] = None


class HotelDetailsResponse(BaseModel):
    Ammenities: list[str] = []
    AmmenityCodes: list[str] = []
    Images: list[HotelImage] = []
    QuantityHotelImages: Optional[int] = None
    Ratings: Optional[HotelRating] = None
    MetaReviews: list[HotelMetaReview] = []
    ReviewsCount: Optional[int] = None


# ---------------------------------------------------------------------------
# Validation (HotelValidation)
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    SearchId: str
    SessionToken: str
    OptionId: Any
    RateId: Any
    IncludeAlternativeCurrencies: bool = False


class CancellationPolicyAmount(BaseModel):
    CurrencyCode: Optional[str] = None
    Fare: Optional[float] = None


class CancellationPolicy(BaseModel):
    Amount: Optional[CancellationPolicyAmount] = None
    DateFrom: Optional[str] = None
    DateTo: Optional[str] = None
    DateFromUTC: Optional[str] = None
    DateToUTC: Optional[str] = None
    DateFromGmtAgency: Optional[str] = None
    DateToGmtAgency: Optional[str] = None
    RoomId: Optional[Any] = None


class ValidDocument(BaseModel):
    Id: int  # API returns int, not str
    Name: Optional[str] = None
    DocumentId: Optional[int] = None


class ValidateResponse(BaseModel):
    ValidDocuments: list[ValidDocument] = []
    CancellationPolicies: list[CancellationPolicy] = []
    CommentContract: Optional[str] = None
    StatusChanged: Optional[str] = None   # Available, NotAvailable, PriceDifference...
    Amount: Optional[Price] = None
    ValidateOptionId: Optional[Any] = None
    TextFare: Optional[str] = None
    AllowOnlyFirstPax: Optional[bool] = None
    RequiredAdultPaxBirthDate: Optional[bool] = None

    @property
    def config_doc_id(self) -> Optional[int]:
        """ConfigurationDocumentId must come from ValidDocuments[0].Id (int)."""
        if self.ValidDocuments:
            return self.ValidDocuments[0].Id
        return None

    @property
    def is_available(self) -> bool:
        return self.StatusChanged in (None, "Available")


# ---------------------------------------------------------------------------
# Booking (HotelBook + HotelConfirm)
# ---------------------------------------------------------------------------

class Traveler(BaseModel):
    RoomNumber: int = 1
    PaxType: Literal["Adult", "Child", "Infant"] = "Adult"
    Gender: Literal["Female", "Male"]
    FirstName: str
    LastName: str
    Phone: str
    Email: str
    DocumentNumber: str
    ConfigurationDocumentId: int   # from ValidateResponse.ValidDocuments[0].Id (int!)
    Nationality: str               # ISO 2-letter country code
    DOB: str                       # "YYYY-MM-DD"
    LoyaltyAccountId: Optional[str] = None

    @field_validator("Nationality")
    @classmethod
    def nationality_uppercase(cls, v: str) -> str:
        return v.upper()


class HotelBookRequest(BaseModel):
    SessionToken: str
    ValidateOptionId: Any
    TravelItineraryId: Optional[str] = None
    Travelers: list[Traveler]


class HotelBookResponse(BaseModel):
    TravelItineraryId: Optional[str] = None
    ReservationId: Optional[int] = None
    Reservation: Optional[dict] = None
    UrlRedirect: Optional[str] = None


# ---------------------------------------------------------------------------
# Confirm (Hotel/Confirm)
# ---------------------------------------------------------------------------

class HotelConfirmRequest(BaseModel):
    HotelReservationId: int
    SessionToken: str


class HotelConfirmResponse(BaseModel):
    Reservation: Optional[dict] = None

    @property
    def is_confirmed(self) -> bool:
        if self.Reservation:
            return self.Reservation.get("Status") == "Confirm"
        return False

    @property
    def supplier_reference(self) -> Optional[str]:
        if self.Reservation:
            return self.Reservation.get("SupplierReferenceCode")
        return None


# ---------------------------------------------------------------------------
# Cancel (Hotel/Cancel)
# ---------------------------------------------------------------------------

class HotelCancelRequest(BaseModel):
    HotelReservationId: int
    SessionToken: str


class HotelCancelResponse(BaseModel):
    Reservation: Optional[dict] = None

    @property
    def is_cancelled(self) -> bool:
        if self.Reservation:
            return self.Reservation.get("Status") == "Cancelled"
        return False
