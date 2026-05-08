"""비용 카테고리 10 분류 + 자동 분류 (vendor 키워드 매칭).

원칙:
- 사용자 입력 우선·미입력 시 자동 분류 (보조)
- 헌법 §11 정합·자동 결정 X·사용자 검수 권장
"""

from __future__ import annotations

from enum import StrEnum


class CategoryName(StrEnum):
    """비용 카테고리 10 분류."""

    MEAL = "meal"
    TRANSPORT = "transport"
    COMM = "comm"
    BOOKS = "books"
    EDUCATION = "education"
    SUPPLIES = "supplies"
    RENT = "rent"
    OUTSOURCING = "outsourcing"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


CATEGORIES: dict[str, str] = {
    CategoryName.MEAL.value: "식대 (업무 미팅·간식)",
    CategoryName.TRANSPORT.value: "교통 (대중교통·택시·주유)",
    CategoryName.COMM.value: "통신 (휴대폰·인터넷·서버)",
    CategoryName.BOOKS.value: "도서·자료 (직무 관련)",
    CategoryName.EDUCATION.value: "교육 (학원·온라인 코스·세미나)",
    CategoryName.SUPPLIES.value: "사무 소모품 (문구·잉크)",
    CategoryName.RENT.value: "임차 (사무실·코워킹)",
    CategoryName.OUTSOURCING.value: "외주비 (디자이너·번역·개발)",
    CategoryName.ENTERTAINMENT.value: "접대 (인정 한도 50%)",
    CategoryName.OTHER.value: "기타",
}


# vendor 키워드 매핑 (자동 분류·사용자 미입력 시)
_VENDOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    CategoryName.MEAL.value: (
        "스타벅스", "투썸", "이디야", "할리스", "맥도날드", "버거킹", "치킨",
        "피자", "한솥", "본죽", "김밥", "분식", "음식점", "카페", "다방",
        "starbucks", "cafe", "restaurant",
    ),
    CategoryName.TRANSPORT.value: (
        "지하철", "버스", "택시", "카카오T", "우티", "코레일", "ktx", "srt",
        "주유소", "휘발유", "경유", "고속도로", "톨게이트", "주차",
        "uber", "kakaotaxi", "gs칼텍스", "sk에너지",
    ),
    CategoryName.COMM.value: (
        "skt", "kt", "lg유플러스", "lgu+", "알뜰폰", "통신비",
        "aws", "gcp", "azure", "vercel", "netlify", "github",
        "도메인", "호스팅", "dns",
    ),
    CategoryName.BOOKS.value: (
        "교보문고", "예스24", "yes24", "알라딘", "인터파크도서",
        "서점", "도서", "책", "ebook",
    ),
    CategoryName.EDUCATION.value: (
        "인프런", "패스트캠퍼스", "코드잇", "노마드코더", "유데미", "udemy",
        "coursera", "edx", "학원", "강의", "세미나", "콘퍼런스",
    ),
    CategoryName.SUPPLIES.value: (
        "다이소", "오피스디포", "모나미", "잉크", "토너", "문구",
        "프린터", "용지",
    ),
    CategoryName.RENT.value: (
        "위워크", "패스트파이브", "스파크플러스", "코워킹", "wework",
        "사무실", "임대료", "월세", "관리비",
    ),
    CategoryName.OUTSOURCING.value: (
        "크몽", "탤런트뱅크", "위시켓", "프리모아", "디자인", "번역",
        "외주", "용역", "업무위탁",
    ),
    CategoryName.ENTERTAINMENT.value: (
        "회식", "송년회", "환영회", "접대", "선물", "기프티콘",
    ),
}


def classify_vendor(vendor: str) -> str:
    """vendor 문자열 → 자동 카테고리 (substring 매칭).

    매칭 X = "other" 반환·사용자 검수 권장.
    """
    if not vendor:
        return CategoryName.OTHER.value

    vendor_lower = vendor.lower()
    for category, keywords in _VENDOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in vendor_lower:
                return category

    return CategoryName.OTHER.value


def is_valid_category(category: str) -> bool:
    """카테고리 유효성 검증."""
    return category in CATEGORIES
