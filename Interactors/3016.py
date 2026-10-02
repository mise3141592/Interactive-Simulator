#!/usr/bin/env python3
"""
포켓몬 배틀트리 인터랙터
Pokemon Battle Tree Interactor

사용법:
    python interactor.py <시나리오_json_경로>

stdin  = 학생(플레이어) 프로그램의 출력
stdout = 학생 프로그램으로 보낼 응답
stderr = 디버그 / 오류 메시지
exit 0 = 정답(Victory)
exit 1 = 오답(WA/RE/TLE)
"""

from __future__ import annotations
import sys
import os
import csv
import io
import json
import random
from fractions import Fraction
from typing import Optional

# ── battle_classes.py 경로 추가 ──────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
##### battle classes 파일의 시작
"""
포켓몬 배틀트리 인터랙터 - 데이터 클래스 구조
Pokemon Gen 7 Battle Tree Interactor - Core Data Structures
"""


import requests
from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class PokemonType(Enum):
    노말   = "노말"
    불꽃   = "불꽃"
    물    = "물"
    풀    = "풀"
    전기   = "전기"
    얼음   = "얼음"
    격투   = "격투"
    독    = "독"
    땅    = "땅"
    비행   = "비행"
    에스퍼  = "에스퍼"
    벌레   = "벌레"
    바위   = "바위"
    고스트  = "고스트"
    드래곤  = "드래곤"
    악    = "악"
    강철   = "강철"
    페어리  = "페어리"


class MoveCategory(Enum):
    물리 = "물리"
    특수 = "특수"
    변화 = "변화"


class StatusCondition(Enum):
    """비휘발성(영속) 상태이상"""
    PSN = "PSN"   # 독
    TOX = "TOX"   # 맹독
    PAR = "PAR"   # 마비
    BRN = "BRN"   # 화상
    SLP = "SLP"   # 잠듦
    FRZ = "FRZ"   # 얼음


class VolatileStatus(Enum):
    """휘발성(배틀 내) 상태이상"""
    CNF = "CNF"   # 혼란
    FLI = "FLI"   # 풀죽음
    BND = "BND"   # 조이기


class Weather(Enum):
    NONE      = "none"
    SUNNY     = "sunny"        # 쾌청
    RAIN      = "rain"         # 비
    SANDSTORM = "sandstorm"    # 모래바람
    HAIL      = "hail"         # 싸라기눈


class Field(Enum):
    NONE = "none"
    ET   = "ET"   # 일렉트릭필드
    GT   = "GT"   # 그래스필드
    MT   = "MT"   # 미스트필드
    PT   = "PT"   # 사이코필드


class RoomEffect(Enum):
    """트릭룸 / 매직룸 / 원더룸 / 중력"""
    TR = "TR"   # 트릭룸
    MR = "MR"   # 매직룸
    WR = "WR"   # 원더룸
    GR = "GR"   # 중력


# ──────────────────────────────────────────────
# 성격 보정 테이블 (7세대 공식 25종)
#
# 표기 기준 (문제 제공 테이블 기반):
#   상승하는 능력치 행 × 열 조합
#   중립 5종: 노력(Hardy) / 온순(Docile) / 수줍음(Bashful) / 변덕(Quirky) / 성실(Serious)
# ──────────────────────────────────────────────

NATURE_MODIFIER: dict[str, dict[str, float]] = {
    # ── 중립 (×1.0 전체, 빈 dict) ──────────────
    "노력":      {},   # Hardy
    "온순":      {},   # Docile
    "수줍음":    {},   # Bashful
    "변덕":      {},   # Quirky
    "성실":      {},   # Serious

    # ── 공격(A) 강화 ────────────────────────────
    "고집":      {"A": 1.1, "C": 0.9},   # Adamant
    "외로움":    {"A": 1.1, "B": 0.9},   # Lonely
    "개구쟁이":  {"A": 1.1, "D": 0.9},   # Naughty
    "용감":      {"A": 1.1, "S": 0.9},   # Brave

    # ── 방어(B) 강화 ────────────────────────────
    "대담":      {"B": 1.1, "A": 0.9},   # Bold
    "장난꾸러기": {"B": 1.1, "C": 0.9},  # Impish
    "촐랑":      {"B": 1.1, "D": 0.9},   # Lax
    "무사태평":  {"B": 1.1, "S": 0.9},   # Relaxed

    # ── 특공(C) 강화 ────────────────────────────
    "조심":      {"C": 1.1, "A": 0.9},   # Modest  ※ 팀의 누리레느·카푸나비나
    "의젓":      {"C": 1.1, "B": 0.9},   # Mild
    "덜렁":      {"C": 1.1, "D": 0.9},   # Rash
    "냉정":      {"C": 1.1, "S": 0.9},   # Quiet

    # ── 특방(D) 강화 ────────────────────────────
    "차분":      {"D": 1.1, "A": 0.9},   # Calm   ※ 팀의 폴리곤2
    "얌전":      {"D": 1.1, "B": 0.9},   # Gentle
    "신중":      {"D": 1.1, "C": 0.9},   # Careful
    "건방":      {"D": 1.1, "S": 0.9},   # Sassy

    # ── 스피드(S) 강화 ──────────────────────────
    "겁쟁이":    {"S": 1.1, "A": 0.9},   # Timid
    "성급":      {"S": 1.1, "B": 0.9},   # Hasty
    "명랑":      {"S": 1.1, "C": 0.9},   # Jolly  ※ 팀의 메타그로스·한카리아스
    "천진난만":  {"S": 1.1, "D": 0.9},   # Naive

    # ── 공격(A) 강화 (고집계) 추가: 고집 테이블에 이미 포함 ──
}

# 유효성 검증 (개발 시 참고용)
assert len(NATURE_MODIFIER) == 25, f"성격 테이블이 25개여야 합니다. 현재: {len(NATURE_MODIFIER)}"


# ──────────────────────────────────────────────
# 번역 유틸리티 (PokeAPI 연동용)
# ──────────────────────────────────────────────

class TranslationTable:
    """
    번역표 CSV(구글 드라이브 공개 URL 또는 로컬 경로)를 로드하여
    한국어 ↔ PokeAPI 영문 식별자 간 변환을 제공합니다.

    항목구분: '포켓몬' | '특성' | '기술'

    사용 예시
    ----------
    # URL에서 로드
    tbl = TranslationTable.from_url(
        "https://drive.google.com/uc?export=download&id=1W4hPTdQFkmzSzksMB-XBMwS1L7w1gi9G"
    )
    # 로컬 파일에서 로드
    tbl = TranslationTable.from_file("/path/to/pokemon_translation_table.csv")

    tbl.ko_to_en("기술", "아이언헤드")   # → "iron-head"
    tbl.en_to_ko("포켓몬", "metagross")  # → "메타그로스"
    """

    def __init__(self, csv_text: str) -> None:
        """
        CSV 텍스트 문자열을 받아 양방향 번역 딕셔너리를 구축합니다.
        직접 호출보다 from_url() / from_file() 클래스 메서드를 권장합니다.
        """
        self._ko_to_en: dict[str, dict[str, str]] = {}
        self._en_to_ko: dict[str, dict[str, str]] = {}

        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            cat = row["항목구분"].strip()
            en  = row["영문식별자"].strip().lower()
            ko  = row["한국어명"].strip()
            self._ko_to_en.setdefault(cat, {})[ko] = en
            self._en_to_ko.setdefault(cat, {})[en] = ko

    @classmethod
    def from_url(cls, url: str) -> "TranslationTable":
        """
        구글 드라이브 등 공개 URL에서 CSV를 다운로드하여 로드합니다.

        구글 드라이브 URL 형식 자동 정규화:
          - 공유 링크 (https://drive.google.com/file/d/<ID>/view?...)
          - usercontent 링크 (https://drive.usercontent.google.com/download?id=<ID>...)
          → 모두 https://drive.google.com/uc?export=download&id=<ID> 로 변환

        동작 확인된 형식:
            url = "https://drive.google.com/uc?export=download&id=<FILE_ID>"
            response = requests.get(url)
        """
        import re

        # ── URL 정규화 ─────────────────────────────────────────
        # 1) https://drive.google.com/file/d/<ID>/view... 형식
        m = re.search(r"drive\.google\.com/file/d/([^/?#]+)", url)
        if m:
            file_id = m.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # 2) https://drive.usercontent.google.com/download?id=<ID>&... 형식
        elif "drive.usercontent.google.com" in url:
            m2 = re.search(r"[?&]id=([^&]+)", url)
            if m2:
                file_id = m2.group(1)
                url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # 3) 이미 uc?export=download&id=... 형식 → 그대로 사용

        try:
            response = requests.get(url)
            response.raise_for_status()
            # utf-8-sig: BOM(\ufeff) 자동 제거
            csv_text = response.content.decode("utf-8-sig")
        except requests.RequestException as e:
            print(f"[TranslationTable] CSV 다운로드 실패: {e}", file=sys.stderr)
            sys.exit(1)
        return cls(csv_text)

    @classmethod
    def from_file(cls, path: str) -> "TranslationTable":
        """로컬 파일 경로에서 CSV를 읽어 로드합니다."""
        try:
            # utf-8-sig: BOM(\ufeff) 자동 제거
            with open(path, encoding="utf-8-sig") as f:
                csv_text = f.read()
        except OSError as e:
            print(f"[TranslationTable] CSV 파일 읽기 실패: {e}", file=sys.stderr)
            sys.exit(1)
        return cls(csv_text)

    def ko_to_en(self, category: str, korean: str) -> Optional[str]:
        """한국어 이름 → PokeAPI 영문 식별자 (없으면 None)."""
        return self._ko_to_en.get(category, {}).get(korean)

    def en_to_ko(self, category: str, english: str) -> Optional[str]:
        """PokeAPI 영문 식별자 → 한국어 이름 (없으면 None)."""
        return self._en_to_ko.get(category, {}).get(english.lower())


# ──────────────────────────────────────────────
# PokeAPI 조회 헬퍼
# ──────────────────────────────────────────────

POKEAPI_BASE = "https://pokeapi.co/api/v2"

def _get_json(url: str) -> Optional[dict]:
    """PokeAPI에서 JSON을 가져옵니다. 실패 시 None 반환."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[PokeAPI 오류] {url}: {e}", file=sys.stderr)
        return None


def fetch_move_data(move_en: str) -> Optional[dict]:
    """
    기술 영문 식별자로 PokeAPI /move/{id} 를 조회합니다.
    반환 딕셔너리 예시 키: type, damage_class, power, accuracy, priority, pp, effect_entries
    """
    return _get_json(f"{POKEAPI_BASE}/move/{move_en}")


def fetch_pokemon_data(pokemon_en: str) -> Optional[dict]:
    """
    포켓몬 영문 식별자로 PokeAPI /pokemon/{id} 를 조회합니다.
    반환 딕셔너리 예시 키: stats, types, abilities
    """
    return _get_json(f"{POKEAPI_BASE}/pokemon/{pokemon_en}")


def fetch_ability_data(ability_en: str) -> Optional[dict]:
    """
    특성 영문 식별자로 PokeAPI /ability/{id} 를 조회합니다.
    """
    return _get_json(f"{POKEAPI_BASE}/ability/{ability_en}")


# ──────────────────────────────────────────────
# 부가효과 데이터
# ──────────────────────────────────────────────

@dataclass
class MoveEffect:
    """
    기술의 부가효과를 표현하는 데이터 클래스.

    chance       : 부가효과 발동 확률 0~100 (100=확정, 0=없음)
    status       : 부여하는 비휘발성 상태이상
    volatile     : 부여하는 휘발성 상태이상
    stat_changes : 랭크 변화 {능력 코드: 변화량}  예) {"A": -1, "S": +1}
    target       : 효과 대상  "foe" | "self"
    flinch_chance: 풀죽음 발동 확률 (chance에서 분리)
    recoil_ratio : 반동 비율 (가한 데미지 기준, 예: 1/3 ≒ 0.333)
    drain_ratio  : 흡수 비율 (가한 데미지 기준, 예: 0.5)
    multi_hit    : 다단히트 (최소 횟수, 최대 횟수)
    """
    chance: int = 0
    status: Optional[StatusCondition] = None
    volatile: Optional[VolatileStatus] = None
    stat_changes: dict[str, int] = field(default_factory=dict)
    target: str = "foe"
    flinch_chance: int = 0
    recoil_ratio: float = 0.0
    drain_ratio: float = 0.0
    multi_hit: Optional[tuple[int, int]] = None


# ──────────────────────────────────────────────
# Move 클래스
# ──────────────────────────────────────────────

@dataclass
class Move:
    """
    포켓몬 기술 하나를 나타내는 데이터 클래스.

    name      : 기술 이름 (한글)
    type_     : 기술 타입
    category  : 물리 / 특수 / 변화
    power     : 위력 (변화기 = 0)
    accuracy  : 명중률 (필중기 = None)
    priority  : 우선도 (기본 0)
    pp        : 최대 PP
    effect    : 부가효과 구조체
    is_z_move : Z기술 여부
    z_power   : Z기술 위력
    contact   : 접촉 여부 (단단한발톱 등 특성 판정에 사용)
    """
    name: str
    type_: PokemonType
    category: MoveCategory
    power: int = 0
    accuracy: Optional[int] = None   # None = 필중
    priority: int = 0
    pp: int = 10
    effect: MoveEffect = field(default_factory=MoveEffect)
    is_z_move: bool = False
    z_power: int = 0
    contact: bool = False

    def __repr__(self) -> str:
        return (
            f"Move({self.name!r}, {self.type_.value}, "
            f"{self.category.value}, pow={self.power}, acc={self.accuracy})"
        )


# ──────────────────────────────────────────────
# Pokemon 클래스
# ──────────────────────────────────────────────

class Pokemon:
    """
    배틀에 참여하는 포켓몬 한 마리의 모든 상태를 관리하는 클래스.

    Parameters
    ----------
    name         : 포켓몬 이름 (한글)
    types        : 타입 목록 (단일 타입이면 요소 1개)
    nature       : 성격 이름 — NATURE_MODIFIER의 키 25종 중 하나
    evs          : 노력치  {"H":252, "A":252, "B":4, ...}  (미지정 능력치 = 0)
    base_stats   : 종족값  {"H":…, "A":…, "B":…, "C":…, "D":…, "S":…}
    ability      : 특성 이름
    moves        : Move 객체 리스트 (최대 4개)
    item         : 지닌물건 이름 (없으면 None)
    ivs          : 개체치  (기본 6V = 전부 31)
    mega_ability : 메가진화 시 특성 (없으면 None)
    mega_types   : 메가진화 시 타입 (없으면 None)
    level        : 레벨 (배틀트리 = 50 고정)
    """

    # 능력치 랭크 배율 테이블
    # index = rank + 6  (rank 범위: -6 ~ +12, 총 19단계)
    # 분자/분모 정수쌍으로 정밀도 손실 없이 계산
    STAT_STAGE_MULTIPLIER: list[tuple[int, int]] = [
        (2, 8), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3),   # -6 ~ -1
        (2, 2),                                              # 0
        (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2),   # +1 ~ +6
        (9, 2), (10, 2), (11, 2), (12, 2), (13, 2), (14, 2),  # +7 ~ +12
    ]

    # 명중/회피 랭크 배율 테이블  index = rank + 6  (rank -6 ~ +6)
    ACC_EVA_STAGE_MULTIPLIER: list[tuple[int, int]] = [
        (1, 3), (3, 8), (3, 7), (1, 2), (7, 12), (17, 30), (33, 60),  # -6 ~ 0
        (4, 3), (7, 5), (5, 3), (7, 4), (8, 5), (3, 2),               # +1 ~ +6
    ]

    def __init__(
        self,
        name: str,
        types: list[PokemonType],
        nature: str,
        evs: dict[str, int],
        base_stats: dict[str, int],
        ability: str,
        moves: list[Move],
        item: Optional[str] = None,
        ivs: Optional[dict[str, int]] = None,
        mega_ability: Optional[str] = None,
        mega_types: Optional[list[PokemonType]] = None,
        level: int = 50,
    ) -> None:

        # ── 입력 검증 ──────────────────────────────
        if nature not in NATURE_MODIFIER:
            print(
                f"[Pokemon.__init__] 알 수 없는 성격입니다: '{nature}'. "
                f"가능한 성격: {list(NATURE_MODIFIER.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)
        if len(moves) > 4:
            print(
                f"[Pokemon.__init__] 기술은 최대 4개입니다. "
                f"입력된 기술 수: {len(moves)}",
                file=sys.stderr,
            )
            sys.exit(1)

        # ── 기본 정보 ──────────────────────────────
        self.name = name
        self.base_types: list[PokemonType] = list(types)   # 원본 타입 (변화 전 보존)
        self.types: list[PokemonType] = list(types)         # 현재 타입 (타입변화 기술 반영)
        self.nature = nature
        self.level = level

        # ── 능력치 기반 데이터 ─────────────────────
        self.base_stats: dict[str, int] = base_stats
        self.evs: dict[str, int] = {s: evs.get(s, 0) for s in "HABCDS"}
        self.ivs: dict[str, int] = ivs if ivs is not None else {s: 31 for s in "HABCDS"}

        # ── 실수치 계산 (레벨 50, 6V, 노력치 반영) ─
        self.max_stats: dict[str, int] = self._calc_all_stats()
        self.current_hp: int = self.max_stats["H"]

        # ── 랭크 (배틀 중 변화, -6 ~ +12) ─────────
        self.rank: dict[str, int] = {s: 0 for s in ["A", "B", "C", "D", "S", "명", "회", "급"]}

        # ── 특성 / 아이템 ──────────────────────────
        self.ability: str = ability
        self.base_ability: str = ability         # 메가진화 전 원본 보존
        self.item: Optional[str] = item
        self.mega_ability: Optional[str] = mega_ability
        self.mega_types: Optional[list[PokemonType]] = mega_types
        self.is_mega: bool = False
        self.z_used: bool = False                # Z기술 사용 여부 (배틀 중 1회)

        # ── 기술 ───────────────────────────────────
        self.moves: list[Move] = moves
        self.locked_move: Optional[str] = None   # 앙코르/구애/역린 — 이 기술만 사용 가능
        self.disabled_move: Optional[str] = None # 사슬묶기(Disable) — 이 기술 사용 불가
        self.disable_counter: int = 0            # 사슬묶기 잔여 턴

        # ── 비휘발성 상태이상 (필드 밖에서도 유지) ─
        self.status: Optional[StatusCondition] = None
        self.toxic_counter: int = 0              # 맹독 누적 카운터 (1턴→1/16, n턴→n/16)
        self.sleep_counter: int = 0              # 잠듦 잔여 턴

        # ── 휘발성 상태이상 (배틀 중에만 유지) ────
        self.volatile_statuses: set[VolatileStatus] = set()
        self.confusion_counter: int = 0          # 혼란 잔여 턴

        # ── 배틀 내 임시 플래그 ───────────────────
        self.is_fainted: bool = False
        self.protect_active: bool = False        # 방어 / 칼막기 / 맹독방어 등
        self.substitute_hp: int = 0              # 대타출동 HP (0 = 미사용)
        self.encore_counter: int = 0             # 앙코르 잔여 턴
        self.last_used_move: Optional[str] = None  # 직전 턴 사용 기술
        self.thrash_counter: int = 0             # 역린 / 화염수레바퀴 등 연속 턴
        self.choice_locked: bool = False         # 구애안경/구애스카프/구애머리띠 고정
        self.charge_move: Optional[str] = None  # 충전 중인 2턴 기술 이름
        self.charge_invulnerable: bool = False  # 충전 중 무적 여부
        self.slow_start_counter: int = 0         # 슬로스타트 경과 턴 수
        self.been_attacked: bool = False         # 이번 턴 공격받음 여부 (애널라이즈용)
        self.stat_dropped_this_turn: bool = False  # 이번 턴 랭크 하락 여부 (불굴의마음용)
        self.ko_count: int = 0                   # 쓰러뜨린 수 (자기과신/정의의마음용)

    # ── 실수치 계산 ────────────────────────────────

    def _calc_stat(self, stat: str) -> int:
        """단일 능력치 실수치 계산 (레벨 50 공식, 소수점 내림)."""
        base = self.base_stats[stat]
        iv   = self.ivs[stat]
        ev   = self.evs.get(stat, 0)
        if stat == "H":
            # HP = floor((base×2 + IV + floor(EV/4)) × Lv/100) + Lv + 10
            return int((base * 2 + iv + ev // 4) * self.level // 100) + self.level + 10
        else:
            # 기타 = floor((floor((base×2 + IV + floor(EV/4)) × Lv/100) + 5) × 성격보정)
            raw = int((base * 2 + iv + ev // 4) * self.level // 100) + 5
            mod = NATURE_MODIFIER.get(self.nature, {}).get(stat, 1.0)
            return int(raw * mod)

    def _calc_all_stats(self) -> dict[str, int]:
        return {s: self._calc_stat(s) for s in "HABCDS"}

    # ── 메가진화 ───────────────────────────────────

    def mega_evolve(self) -> None:
        """
        메가진화를 수행합니다.
        이미 메가진화 상태이거나 메가스톤이 없으면 stderr 출력 후 종료합니다.
        """
        if self.is_mega:
            print(
                f"[mega_evolve] {self.name}은(는) 이미 메가진화 상태입니다.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not self.mega_ability:
            print(
                f"[mega_evolve] {self.name}은(는) 메가진화를 할 수 없습니다 "
                f"(mega_ability가 설정되지 않음).",
                file=sys.stderr,
            )
            sys.exit(1)
        self.is_mega = True
        self.ability = self.mega_ability
        if self.mega_types:
            self.types = list(self.mega_types)

    # ── 랭크 보정 실수치 반환 ──────────────────────

    def effective_stat(self, stat: str) -> int:
        """
        랭크 단계를 적용한 배틀 내 실효 능력치를 반환합니다.
        stat: "A" | "B" | "C" | "D" | "S"
        (명중/회피 배율은 별도 acc_eva_multiplier 사용)
        """
        base  = self.max_stats[stat]
        stage = self.rank[stat]
        idx   = max(0, min(stage + 6, len(self.STAT_STAGE_MULTIPLIER) - 1))
        num, den = self.STAT_STAGE_MULTIPLIER[idx]
        return int(base * num / den)

    def acc_eva_multiplier(self, rank_key: str) -> tuple[int, int]:
        """
        명중('명') 또는 회피('회') 랭크에 대한 배율 (분자, 분모) 반환.
        """
        stage = self.rank[rank_key]
        idx   = max(0, min(stage + 6, len(self.ACC_EVA_STAGE_MULTIPLIER) - 1))
        return self.ACC_EVA_STAGE_MULTIPLIER[idx]

    # ── HP 조작 ────────────────────────────────────

    def take_damage(self, amount: int) -> int:
        """데미지를 받고 실제 감소한 HP를 반환합니다. 0 이하가 되면 faint() 호출."""
        # 옹골참 (Sturdy): HP 만빵 → 일격기절 공격을 HP 1로 버팀
        if (self.ability == "옹골참"
                and self.current_hp == self.max_stats["H"]
                and amount >= self.current_hp):
            self.current_hp = 1
            return self.max_stats["H"] - 1
        # 기합의띠 (Focus Sash): HP 만빵 → 일격기절 공격을 HP 1로 버팀 (1회)
        if (self.item == "기합의띠"
                and self.current_hp == self.max_stats["H"]
                and amount >= self.current_hp):
            self.item = None  # 소비
            self.current_hp = 1
            return self.max_stats["H"] - 1
        actual = min(amount, self.current_hp)
        self.current_hp -= actual
        if self.current_hp <= 0:
            self.current_hp = 0
            self.faint()
        return actual

    def heal(self, amount: int) -> int:
        """HP를 회복하고 실제 회복량을 반환합니다. 최대 HP를 초과하지 않습니다."""
        actual = min(amount, self.max_stats["H"] - self.current_hp)
        self.current_hp += actual
        return actual

    def faint(self) -> None:
        """기절 처리 — 휘발성 상태와 고정 기술을 초기화합니다."""
        self.is_fainted = True
        self.volatile_statuses.clear()
        self.confusion_counter = 0
        self.locked_move = None

    # ── 랭크 변화 ──────────────────────────────────

    def change_rank(self, stat: str, delta: int) -> int:
        """
        능력치 랭크를 delta만큼 변화시키고 실제 변화량을 반환합니다.
        범위: -6 ~ +12 (클램핑).
        """
        old = self.rank[stat]
        new = max(-6, min(12, old + delta))
        self.rank[stat] = new
        return new - old

    # ── 상태이상 ───────────────────────────────────

    def apply_status(self, cond: StatusCondition) -> bool:
        """비휘발성 상태이상을 부여합니다. 이미 상태이상이면 False 반환."""
        if self.status is not None:
            return False
        self.status = cond
        if cond == StatusCondition.TOX:
            self.toxic_counter = 1
        return True

    def cure_status(self) -> None:
        """비휘발성 상태이상을 모두 치유합니다."""
        self.status = None
        self.toxic_counter = 0
        self.sleep_counter = 0

    def apply_volatile(self, v: VolatileStatus) -> bool:
        """휘발성 상태이상을 부여합니다. 이미 걸려 있으면 False 반환."""
        if v in self.volatile_statuses:
            return False
        self.volatile_statuses.add(v)
        return True

    def cure_volatile(self, v: VolatileStatus) -> None:
        """특정 휘발성 상태이상을 치유합니다."""
        self.volatile_statuses.discard(v)

    # ── 배틀 종료 시 리셋 ──────────────────────────

    def reset_battle_volatile(self) -> None:
        """
        배틀 종료(또는 교체 출전) 후 휘발성 상태를 초기화합니다.
        비휘발성 상태이상(status, toxic_counter 등)은 유지됩니다.
        메가진화도 해제됩니다.
        """
        self.rank = {s: 0 for s in self.rank}
        self.volatile_statuses.clear()
        self.confusion_counter = 0
        self.locked_move = None
        self.disabled_move = None
        self.disable_counter = 0
        self.protect_active = False
        self.substitute_hp = 0
        self.encore_counter = 0
        self.last_used_move = None
        self.thrash_counter = 0
        self.choice_locked = False
        self.charge_move = None
        self.charge_invulnerable = False
        self.been_attacked = False
        self.stat_dropped_this_turn = False
        if self.is_mega:
            self.is_mega = False
            self.ability = self.base_ability
            self.types = list(self.base_types)

    def __repr__(self) -> str:
        type_str = "/".join(t.value for t in self.types)
        return (
            f"Pokemon({self.name!r}, [{type_str}], "
            f"HP={self.current_hp}/{self.max_stats['H']}, "
            f"status={self.status})"
        )


# ──────────────────────────────────────────────
# BattleState 클래스
# ──────────────────────────────────────────────

@dataclass
class RoomState:
    """단일 룸/중력 효과의 활성화 상태와 잔여 턴을 보관합니다."""
    active: bool = False
    turns_left: int = 0


class BattleState:
    """
    현재 배틀 필드 전체의 환경 상태를 관리하는 클래스.

    날씨, 필드, 룸 효과(트릭룸·매직룸·원더룸·중력)를 독립적으로 추적합니다.
    각 효과는 기본 5턴이며, 일부 아이템에 의해 8턴으로 연장될 수 있습니다.
    """

    WEATHER_DURATION: int = 5
    FIELD_DURATION:   int = 5
    ROOM_DURATION:    int = 5

    def __init__(self) -> None:
        # ── 날씨 ──────────────────────────────────
        self.weather: Weather = Weather.NONE
        self.weather_turns_left: int = 0

        # ── 필드 ──────────────────────────────────
        self.field: Field = Field.NONE
        self.field_turns_left: int = 0

        # ── 룸 & 중력 (각각 독립 타이머) ──────────
        self.rooms: dict[RoomEffect, RoomState] = {r: RoomState() for r in RoomEffect}

        # ── 이력 로그 (디버깅용) ───────────────────
        self._history: list[str] = []

    # ── 날씨 ────────────────────────────────────────

    def set_weather(self, w: Weather, turns: int = WEATHER_DURATION) -> None:
        """날씨를 설정합니다. Weather.NONE이면 즉시 해제합니다."""
        self.weather = w
        self.weather_turns_left = turns if w != Weather.NONE else 0
        self._history.append(f"Weather → {w.value} ({turns}t)")

    def tick_weather(self) -> bool:
        """턴 종료 시 날씨 카운터를 감소합니다. 종료되면 True 반환."""
        if self.weather == Weather.NONE:
            return False
        self.weather_turns_left -= 1
        if self.weather_turns_left <= 0:
            prev = self.weather
            self.weather = Weather.NONE
            self._history.append(f"Weather {prev.value} ended")
            return True
        return False

    # ── 필드 ────────────────────────────────────────

    def set_field(self, f: Field, turns: int = FIELD_DURATION) -> None:
        """필드 효과를 설정합니다. Field.NONE이면 즉시 해제합니다."""
        self.field = f
        self.field_turns_left = turns if f != Field.NONE else 0
        self._history.append(f"Field → {f.value} ({turns}t)")

    def tick_field(self) -> bool:
        """턴 종료 시 필드 카운터를 감소합니다. 종료되면 True 반환."""
        if self.field == Field.NONE:
            return False
        self.field_turns_left -= 1
        if self.field_turns_left <= 0:
            prev = self.field
            self.field = Field.NONE
            self._history.append(f"Field {prev.value} ended")
            return True
        return False

    # ── 룸 & 중력 ───────────────────────────────────

    def set_room(self, r: RoomEffect, turns: int = ROOM_DURATION) -> None:
        """
        룸 효과를 활성화합니다.
        이미 활성화 중이면 토글(해제)합니다. (트릭룸 재사용 시 즉시 해제)
        """
        state = self.rooms[r]
        if state.active:
            state.active = False
            state.turns_left = 0
            self._history.append(f"Room {r.value} cancelled (toggled off)")
        else:
            state.active = True
            state.turns_left = turns
            self._history.append(f"Room {r.value} started ({turns}t)")

    def tick_rooms(self) -> list[RoomEffect]:
        """턴 종료 시 활성화된 모든 룸의 카운터를 감소합니다. 종료된 룸 리스트 반환."""
        ended: list[RoomEffect] = []
        for r, state in self.rooms.items():
            if state.active:
                state.turns_left -= 1
                if state.turns_left <= 0:
                    state.active = False
                    ended.append(r)
                    self._history.append(f"Room {r.value} ended")
        return ended

    # ── 편의 조회 메서드 ────────────────────────────

    def is_trick_room(self)  -> bool: return self.rooms[RoomEffect.TR].active
    def is_gravity(self)     -> bool: return self.rooms[RoomEffect.GR].active
    def is_magic_room(self)  -> bool: return self.rooms[RoomEffect.MR].active
    def is_wonder_room(self) -> bool: return self.rooms[RoomEffect.WR].active

    # ── 전체 틱 ─────────────────────────────────────

    def tick_all(self) -> dict:
        """
        턴 종료 시 날씨·필드·룸 타이머를 일괄 감소합니다.
        반환: {"weather_ended": bool, "field_ended": bool, "rooms_ended": list[RoomEffect]}
        """
        return {
            "weather_ended": self.tick_weather(),
            "field_ended":   self.tick_field(),
            "rooms_ended":   self.tick_rooms(),
        }

    def reset(self) -> None:
        """배틀 시작 전 모든 환경을 초기화합니다."""
        self.weather = Weather.NONE
        self.weather_turns_left = 0
        self.field = Field.NONE
        self.field_turns_left = 0
        for state in self.rooms.values():
            state.active = False
            state.turns_left = 0
        self._history.clear()

    def summary(self) -> str:
        active_rooms = [r.value for r, s in self.rooms.items() if s.active]
        return (
            f"BattleState("
            f"weather={self.weather.value}({self.weather_turns_left}t), "
            f"field={self.field.value}({self.field_turns_left}t), "
            f"rooms={active_rooms})"
        )

    def __repr__(self) -> str:
        return self.summary()


# ══════════════════════════════════════════════
#  배틀 로직 (Battle Logic)
# ══════════════════════════════════════════════

import random
from fractions import Fraction

# ──────────────────────────────────────────────
# 타입 상성 테이블  (7세대 기준)
# 값: Fraction  2=2배 / Fraction(1,2)=0.5배 / 0=무효
# ──────────────────────────────────────────────

_H = Fraction(1, 2)   # 0.5배 (효과가 별로)
_I = Fraction(0)      # 0배   (효과 없음)
_N = Fraction(1)      # 1배   (보통)
_S = Fraction(2)      # 2배   (효과 굉장)

# 행: 공격 타입 순서  (PokemonType Enum 선언 순서와 일치)
# 열: 방어 타입 순서
_TYPE_ORDER: list[str] = [
    "노말","불꽃","물","풀","전기","얼음","격투","독",
    "땅","비행","에스퍼","벌레","바위","고스트","드래곤","악","강철","페어리",
]

# [공격타입_idx][방어타입_idx] = 배율
_TYPE_CHART_RAW: list[list[Fraction]] = [
#  노  불  물  풀  전  얼  격  독  땅  비  에  벌  바  고  드  악  강  페
  [_N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _H, _I, _N, _N, _H, _N],  # 노말
  [_N, _H, _H, _S, _N, _S, _N, _N, _N, _N, _N, _S, _H, _N, _H, _N, _S, _N],  # 불꽃
  [_N, _S, _H, _H, _N, _N, _N, _N, _S, _N, _N, _N, _S, _N, _H, _N, _N, _N],  # 물
  [_N, _H, _S, _H, _N, _N, _N, _H, _S, _H, _N, _H, _S, _N, _H, _N, _H, _N],  # 풀
  [_N, _N, _S, _H, _H, _N, _N, _N, _I, _S, _N, _N, _N, _N, _H, _N, _N, _N],  # 전기
  [_N, _H, _H, _S, _N, _H, _N, _N, _S, _S, _N, _N, _N, _N, _S, _N, _H, _N],  # 얼음
  [_S, _N, _N, _N, _N, _S, _N, _H, _N, _H, _H, _H, _S, _I, _N, _S, _S, _H],  # 격투
  [_N, _N, _N, _S, _N, _N, _N, _H, _H, _N, _N, _N, _H, _H, _N, _N, _I, _S],  # 독
  [_N, _S, _N, _H, _S, _N, _N, _S, _N, _I, _N, _H, _S, _N, _N, _N, _S, _N],  # 땅
  [_N, _N, _N, _S, _H, _N, _S, _N, _N, _N, _N, _S, _H, _N, _N, _N, _H, _N],  # 비행
  [_N, _N, _N, _N, _N, _N, _S, _S, _N, _N, _H, _N, _N, _N, _N, _I, _H, _N],  # 에스퍼
  [_N, _H, _N, _S, _N, _N, _H, _H, _N, _H, _S, _N, _N, _H, _N, _S, _H, _H],  # 벌레
  [_N, _S, _N, _N, _N, _S, _H, _N, _H, _S, _N, _S, _N, _N, _N, _N, _H, _N],  # 바위
  [_I, _N, _N, _N, _N, _N, _N, _N, _N, _N, _S, _N, _N, _S, _N, _H, _N, _N],  # 고스트
  [_N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _N, _S, _N, _H, _I],  # 드래곤
  [_N, _N, _N, _N, _N, _N, _H, _N, _N, _N, _S, _N, _N, _S, _N, _H, _N, _H],  # 악
  [_N, _H, _H, _N, _H, _S, _N, _N, _N, _N, _N, _N, _S, _N, _N, _N, _H, _S],  # 강철
  [_N, _H, _N, _N, _N, _N, _S, _H, _N, _N, _N, _N, _N, _N, _S, _S, _H, _N],  # 페어리
]

# 빠른 조회용 딕셔너리로 변환
TYPE_CHART: dict[str, dict[str, Fraction]] = {}
for _atk_i, _atk in enumerate(_TYPE_ORDER):
    TYPE_CHART[_atk] = {}
    for _def_j, _def in enumerate(_TYPE_ORDER):
        TYPE_CHART[_atk][_def] = _TYPE_CHART_RAW[_atk_i][_def_j]


def get_type_effectiveness(move_type: PokemonType, defender_types: list[PokemonType]) -> Fraction:
    """
    공격 타입 vs 방어 포켓몬 타입(듀얼 타입 포함) 상성 배율을 반환합니다.
    반환값: Fraction (0, 1/4, 1/2, 1, 2, 4 중 하나)
    """
    result = Fraction(1)
    atk = move_type.value
    for def_type in defender_types:
        result *= TYPE_CHART.get(atk, {}).get(def_type.value, Fraction(1))
    return result


# ──────────────────────────────────────────────
# 특성 보정 헬퍼 (데미지 계산용)
# ──────────────────────────────────────────────

def _ability_atk_modifier(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
    battle: "BattleState",
) -> Fraction:
    """
    공격측 특성에 의한 데미지 배율을 반환합니다.
    (단단한발톱, 철주먹, 기술스킨 계열 등 공격 배율 특성)
    """
    ability = attacker.ability
    mtype   = move.type_
    mcat    = move.category

    # 단단한발톱 (Tough Claws): 접촉기 ×1.3
    if ability == "단단한발톱" and move.contact:
        return Fraction(13, 10)

    # 철주먹 (Iron Fist): 펀치 기술 ×1.2  (PUNCH_MOVES 집합 참조)
    if ability == "철주먹" and move.name in PUNCH_MOVES:
        return Fraction(6, 5)

    # 불꽃엔진 (Blaze): HP 1/3 이하, 불꽃 ×1.5
    if ability == "맹화" and mtype == PokemonType.불꽃:
        if attacker.current_hp <= attacker.max_stats["H"] // 3:
            return Fraction(3, 2)

    # 급류 (Torrent): HP 1/3 이하, 물 ×1.5
    if ability == "급류" and mtype == PokemonType.물:
        if attacker.current_hp <= attacker.max_stats["H"] // 3:
            return Fraction(3, 2)

    # 우거짐 (Overgrow): HP 1/3 이하, 풀 ×1.5
    if ability == "우거짐" and mtype == PokemonType.풀:
        if attacker.current_hp <= attacker.max_stats["H"] // 3:
            return Fraction(3, 2)

    # 벌레의알림 (Swarm): HP 1/3 이하, 벌레 ×1.5
    if ability == "벌레의알림" and mtype == PokemonType.벌레:
        if attacker.current_hp <= attacker.max_stats["H"] // 3:
            return Fraction(3, 2)

    # 모래의힘 (Sand Force): 모래바람 중 바위/강철/땅 ×1.3
    if ability == "모래의힘" and battle.weather == Weather.SANDSTORM:
        if mtype in (PokemonType.바위, PokemonType.강철, PokemonType.땅):
            return Fraction(13, 10)

    """
    _ability_atk_modifier의 확장판: 추가 특성 보정을 반영합니다.
    기존 함수와 결과를 곱해서 사용합니다.
    """

    # 강한턱 (Strong Jaw): 물기 기술 ×1.5
    if ability == "옹골찬턱" and move.name in BITE_MOVES:
        return Fraction(3, 2)

    # 철주먹 (Iron Fist): 펀치 기술 ×1.2
    if ability == "철주먹" and move.name in PUNCH_MOVES:
        return Fraction(6, 5)

    # 메가런처 (Mega Launcher): 파동 기술 ×1.5
    if ability == "메가런처" and move.name in PULSE_MOVES:
        return Fraction(3, 2)

    # 수포 (Water Bubble): 물 공격 ×2
    if ability == "수포" and mtype == PokemonType.물:
        return Fraction(2)


    # 순수한힘 (Pure Power / Huge Power): 물리 공격 ×2
    if ability in ("순수한힘", "괴력") and move.category == MoveCategory.물리:
        return Fraction(2)

    # 애널라이즈 (Analytic): 후공 시 위력 ×1.3
    if ability == "애널라이즈" and attacker.been_attacked:
        return Fraction(13, 10)

    # 강철술사 (Steelworker): 강철 기술 ×1.5
    if ability == "강철술사" and mtype == PokemonType.강철:
        return Fraction(3, 2)

    # 통찰 (Analytic / Contrary 아님): 후공 시 ×1.3 → 위에서 처리됨

    # 비비드바디 (Competitive): 랭크 하락 시 특공 +2 (apply_move_secondary에서 처리)

    # 우격다짐 (Sheer Force): 추가효과 있는 기술 ×1.3 (부가효과 제거)
    if ability == "우격다짐" and move.effect.chance > 0:
        return Fraction(13, 10)

    # 서투름 (Reckless): 반동 있는 기술 ×1.2
    if ability == "서투름" and move.effect.recoil_ratio > 0:
        return Fraction(6, 5)

    # 심록 (Overgrow): HP 1/3 이하, 풀 ×1.5
    if ability == "심록" and move.type_ == PokemonType.풀:
        if attacker.current_hp <= attacker.max_stats["H"] // 3:
            return Fraction(3, 2)

    # 독폭주 (Toxic Boost): 독/맹독 상태 시 물리 ×1.5
    if ability == "독폭주" and move.category == MoveCategory.물리:
        if attacker.status in (StatusCondition.PSN, StatusCondition.TOX):
            return Fraction(3, 2)

    # 타오르는불꽃 (Guts variant: Flash Fire): 화상 상태 시 공격 ×1.5 (근성과 별도)
    if ability == "타오르는불꽃" and move.type_ == PokemonType.불꽃:
        if attacker.status == StatusCondition.BRN:
            return Fraction(3, 2)

    # 하늘의은총 (Serene Grace): 부가효과 확률 2배 → 데미지 보정 없음 (부가효과 적용 시 처리)

    # 스나이퍼 (Sniper): 급소 배율 ×2.25 → calculate_damage 내 crit_mod에서 처리
    # 대운 (Super Luck): 급소율 +1 → 급소 판정에서 처리

    # 전기엔진 (Electric surge) 관련은 필드 보정으로 처리
    return Fraction(1)


def _ability_def_modifier(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
    battle: "BattleState",
) -> Fraction:
    """
    방어측 특성에 의한 데미지 배율을 반환합니다.
    (두꺼운지방, 수포, 건조피부 등 피해 경감/무효 특성)
    """
    ability = defender.ability
    mtype   = move.type_
    mcat    = move.category

    # 두꺼운지방 (Thick Fat): 불꽃/얼음 ×0.5
    if ability == "두꺼운지방" and mtype in (PokemonType.불꽃, PokemonType.얼음):
        return Fraction(1, 2)

    # 수포 (Water Bubble): 불꽃 피해 ×0.5
    if ability == "수포" and mtype == PokemonType.불꽃:
        return Fraction(1, 2)

    # 건조피부 (Dry Skin): 불꽃 ×1.25
    if ability == "건조피부" and mtype == PokemonType.불꽃:
        return Fraction(5, 4)

    # 퍼코트 (Fur Coat): 물리 ×0.5
    if ability == "퍼코트" and mcat == MoveCategory.물리:
        return Fraction(1, 2)

    # 멀티스케일 (Multiscale): HP 최대 시 ×0.5
    if ability == "멀티스케일" and defender.current_hp == defender.max_stats["H"]:
        return Fraction(1, 2)

    # 그림자방패 (Shadow Shield): HP 최대 시 ×0.5 (7세대 루나아라)
    if ability == "스펙터가드" and defender.current_hp == defender.max_stats["H"]:
        return Fraction(1, 2)

    # 필터 (Filter) / 방음 (Solid Rock) / 하드록: 효과가 굉장할 때 ×0.75
    type_eff = get_type_effectiveness(move.type_, defender.types)
    if ability in ("필터", "방음", "프리즘아머", "하드록") and type_eff > Fraction(1):
        return Fraction(3, 4)

    # 진화의휘석 (Eviolite): 방어/특방 ×1.5
    if defender.item == "진화의휘석":
        return Fraction(3, 2)

    # 돌격조끼 (Assault Vest): 특수기 특방 ×1.5
    if defender.item == "돌격조끼" and mcat == MoveCategory.특수:
        return Fraction(3, 2)

    # 이상한비늘 (Marvel Scale): 상태이상 시 방어 ×1.5
    if (ability == "이상한비늘"
            and defender.status is not None
            and mcat == MoveCategory.물리):
        return Fraction(3, 2)

    # 틀깨기 계열: 방어 특성 무시 여부는 attacker 특성으로 판정
    # (틀깨기 attacker는 부유/스펙터가드 등 방어 특성 무시)

    return Fraction(1)


def _weather_modifier(move: "Move", battle: "BattleState") -> Fraction:
    """날씨에 의한 데미지 배율."""
    w = battle.weather
    t = move.type_
    if w == Weather.SUNNY:
        if t == PokemonType.불꽃:
            return Fraction(3, 2)
        if t == PokemonType.물:
            return Fraction(1, 2)
    elif w == Weather.RAIN:
        if t == PokemonType.물:
            return Fraction(3, 2)
        if t == PokemonType.불꽃:
            return Fraction(1, 2)
    return Fraction(1)


def _field_modifier(
    move: "Move",
    attacker: "Pokemon",
    battle: "BattleState",
) -> Fraction:
    """
    필드 효과에 의한 데미지 배율.
    필드 보정은 땅에 발이 닿아 있는 포켓몬에게만 적용됩니다.
    (비행 타입 / 부유 특성은 땅에 없는 것으로 처리)
    """
    field = battle.field
    if field == Field.NONE:
        return Fraction(1)

    grounded = (
        PokemonType.비행 not in attacker.types
        and attacker.ability not in ("부유",)
    )
    if not grounded:
        return Fraction(1)

    t = move.type_
    if field == Field.ET and t == PokemonType.전기:
        return Fraction(3, 2)
    if field == Field.GT and t == PokemonType.풀:
        return Fraction(3, 2)
    # 사이코필드는 에스퍼 Z기술 보정(별도 처리) 및 선제 기술 차단에 사용
    return Fraction(1)


def _burn_modifier(attacker: "Pokemon", move: "Move") -> Fraction:
    """
    화상 패널티: 물리 기술 사용 시 ×0.5
    (근성 특성이면 화상 패널티 무시)
    """
    if (
        attacker.status == StatusCondition.BRN
        and move.category == MoveCategory.물리
        and attacker.ability != "근성"
    ):
        return Fraction(1, 2)
    return Fraction(1)


# ──────────────────────────────────────────────
# calculate_damage
# ──────────────────────────────────────────────

def calculate_damage(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
    battle: "BattleState",
    *,
    is_critical: Optional[bool] = None,
    random_roll: Optional[float] = None,
) -> dict:
    """
    7세대 공식에 따른 데미지를 계산합니다.

    공식 (모든 소수점은 floor):
        Damage = floor(floor(floor(2×Lv/5 + 2) × A × P / D / 50 + 2)
                       × STAB × TypeEff × 기타보정 × 랜덤)

    Parameters
    ----------
    attacker      : 공격하는 포켓몬
    defender      : 방어하는 포켓몬
    move          : 사용하는 기술
    battle        : 현재 배틀 상태 (날씨·필드 참조)
    is_critical   : 급소 여부 직접 지정 (None이면 확률로 결정)
    random_roll   : 난수 직접 지정 0.85~1.00 (None이면 무작위)

    Returns
    -------
    dict with keys:
        damage        : int  실제 데미지 값
        is_critical   : bool 급소 여부
        random_roll   : float 적용된 난수
        type_eff      : Fraction 타입 상성 배율
        is_stab       : bool 자속 여부
    """
    if move.category == MoveCategory.변화:
        return {
            "damage": 0,
            "is_critical": False,
            "random_roll": 1.0,
            "type_eff": Fraction(1),
            "is_stab": False,
        }

    # ── 급소 판정 ──────────────────────────────
    # 7세대 급소율: C랭크 0→1/16, 1→1/8, 2→1/2, 3이상→확정
    if is_critical is None:
        crit_rank = attacker.rank.get("급", 0)
        crit_rank = max(0, crit_rank)
        # 예리한손톱: 급소율 +1
        if attacker.item == "예리한손톱":
            crit_rank += 1
        # 대운: 급소율 +1
        if attacker.ability == "대운":
            crit_rank += 1
        if   crit_rank == 0: crit_chance = Fraction(1, 16)
        elif crit_rank == 1: crit_chance = Fraction(1, 8)
        elif crit_rank == 2: crit_chance = Fraction(1, 2)
        else:                crit_chance = Fraction(1)
        is_critical = random.random() < float(crit_chance)

    # ── 공격 / 방어 능력치 결정 ───────────────
    if move.category == MoveCategory.물리:
        atk_stat_key = "A"
        def_stat_key = "B"
    else:  # 특수
        atk_stat_key = "C"
        def_stat_key = "D"

    # 급소 시: 공격 랭크는 음수 무시, 방어 랭크는 양수 무시
    atk_rank = attacker.rank[atk_stat_key]
    def_rank = defender.rank[def_stat_key]
    if is_critical:
        atk_rank = max(atk_rank, 0)
        def_rank = min(def_rank, 0)

    # 원더룸 활성화 시 방어·특방 교환
    if battle.is_wonder_room():
        def_stat_key = "B" if def_stat_key == "D" else "D"

    # 실수치에 랭크 배율 적용 (Pokemon.STAT_STAGE_MULTIPLIER 사용)
    def _ranked(base_val: int, rank: int) -> int:
        idx = max(0, min(rank + 6, len(Pokemon.STAT_STAGE_MULTIPLIER) - 1))
        num, den = Pokemon.STAT_STAGE_MULTIPLIER[idx]
        return int(base_val * num / den)

    A = _ranked(attacker.max_stats[atk_stat_key], atk_rank)
    D = _ranked(defender.max_stats[def_stat_key], def_rank)

    # 모래바람 중 바위 타입의 특방 1.5배
    if (
        battle.weather == Weather.SANDSTORM
        and PokemonType.바위 in defender.types
        and def_stat_key == "D"
    ):
        D = int(D * 3 / 2)

    P = move.power   # 기술 위력

    # ── 기본 데미지 (소수점 내림) ─────────────
    base = int(int(int(2 * attacker.level / 5 + 2) * A * P / D / 50) + 2)

    # ── 각종 보정 배율 적용 ───────────────────
    # 자속 (STAB)
    is_stab = move.type_ in attacker.types
    if is_stab:
        # 적응력 특성: 자속 ×2.0
        if attacker.ability == "적응력":
            stab = Fraction(2)
        else:
            stab = Fraction(3, 2)
    else:
        stab = Fraction(1)

    # 타입 상성
    type_eff = get_type_effectiveness(move.type_, defender.types)
    if type_eff == 0:
        # 무효 → 즉시 0 반환
        return {
            "damage": 0,
            "is_critical": is_critical,
            "random_roll": random_roll or 1.0,
            "type_eff": Fraction(0),
            "is_stab": is_stab,
        }

    # 날씨 보정
    weather_mod = _weather_modifier(move, battle)

    # 급소 보정: ×1.5 (스나이퍼는 ×2.25)
    if is_critical:
        crit_mod = Fraction(9, 4) if attacker.ability == "스나이퍼" else Fraction(3, 2)
    else:
        crit_mod = Fraction(1)

    # 난수 (0.85 ~ 1.00, 1/100 단위 16단계)
    if random_roll is None:
        random_roll = random.randint(85, 100) / 100.0
    random_frac = Fraction(int(random_roll * 100), 100)

    # 화상 패널티
    burn_mod = _burn_modifier(attacker, move)

    # 필드 보정
    field_mod = _field_modifier(move, attacker, battle)

    # 공격측 특성 보정
    atk_ability_mod = _ability_atk_modifier(attacker, defender, move, battle)
    # _apply_ability_atk_modifier_extended: 추가 특성 보정 (옹골찬턱 등)
    atk_ability_mod = atk_ability_mod * _apply_ability_atk_modifier_extended(
        attacker, defender, move, battle)

    # 방어측 특성 보정 (틀깨기 계열은 방어 특성 무시)
    if attacker.ability in ("틀깨기", "터보블레이즈", "테라볼티지"):
        def_ability_mod = Fraction(1)
    else:
        def_ability_mod = _ability_def_modifier(attacker, defender, move, battle)

    # ── 공격자 아이템 보정 ───────────────────────
    item_mod = Fraction(1)
    a_item = attacker.item or ""
    if a_item == "생명의구슬":
        item_mod = Fraction(13, 10)
    elif a_item == "달인의띠" and type_eff > Fraction(1):
        item_mod = Fraction(6, 5)
    # 조개껍질방울: 데미지의 1/8 회복 → apply_move_secondary_effect에서 처리
    # 타입 강화 아이템 (×1.2)
    elif a_item in ("검은띠",)    and move.type_ == PokemonType.격투: item_mod = Fraction(6,5)
    elif a_item in ("목탄",)      and move.type_ == PokemonType.불꽃: item_mod = Fraction(6,5)
    elif a_item in ("녹지않는얼음",) and move.type_ == PokemonType.얼음: item_mod = Fraction(6,5)
    elif a_item in ("자석",)      and move.type_ == PokemonType.전기: item_mod = Fraction(6,5)
    elif a_item in ("실크스카프",) and move.type_ == PokemonType.노말: item_mod = Fraction(6,5)
    elif a_item == "검은진흙"     and move.type_ == PokemonType.독: item_mod = Fraction(6,5)
    # 딱딱한돌: 바위 ×1.5
    elif a_item == "딱딱한돌"    and move.type_ == PokemonType.바위: item_mod = Fraction(3,2)
    # 예리한손톱: 급소율 +1 (데미지 보정 없음, 급소 판정에서 처리)
    # 초점렌즈/광각렌즈: 명중률 (데미지 보정 없음)
    # 큰뿌리: 흡수량 1.3배 (drain 처리에서)

    # ── 힘의머리띠/박식안경: 물리/특수 ×1.1 ────────────────
    if a_item == "힘의머리띠" and move.category == MoveCategory.물리:
        item_mod = Fraction(11, 10)
    elif a_item == "박식안경" and move.category == MoveCategory.특수:
        item_mod = Fraction(11, 10)

    # ── 구애 시리즈: ×1.5 + 기술 고정 ──────────────────────
    choice_mod = Fraction(1)
    if a_item == "구애띠"    and move.category == MoveCategory.물리:  choice_mod = Fraction(3, 2)
    if a_item == "구애안경"  and move.category == MoveCategory.특수:  choice_mod = Fraction(3, 2)

    # ── 방어자 아이템 보정 (반감열매) ────────────
    berry_mod = Fraction(1)
    d_item = defender.item or ""
    # 루미열매: 효과 굉장한 바위 타입 피해 50% 감소
    if (d_item == "루미열매"
            and move.type_ == PokemonType.바위
            and type_eff > Fraction(1)):
        berry_mod = Fraction(1, 2)
        defender.item = None
    else:
        # 타입별 반감열매
        berry_type = RESIST_BERRY.get(move.type_.value)
        if berry_type and d_item == berry_type and type_eff > Fraction(1):
            berry_mod = Fraction(1, 2)
            defender.item = None  # 열매 소비
    # 돌격조끼: 특방 1.5배 (def_modifier에서 처리됨, 특수기 변화기 사용 불가)
    # 울퉁불퉁멧: 접촉 시 상대 데미지 (apply_contact_ability에서 처리)
    # 약점보험: 효과 굉장한 기술 맞으면 A+C+2 (apply_move_secondary에서 처리)
    # 풍선: 땅 기술 무효 (명중 판정 전에 처리 필요)

    # ── 최종 데미지 계산 (소수점 내림) ─────────
    # 7세대 공식의 체인 floor 순서:
    # 1) base (이미 계산)
    # 2) × 날씨
    # 3) × 급소
    # 4) floor → × 랜덤
    # 5) floor → × STAB
    # 6) floor → × 타입상성 (체인 곱, 각 단계에서 floor 없이 누적 후 마지막 floor)
    # 7) 기타 보정들은 각각 floor 적용
    dmg = base
    dmg = int(dmg * weather_mod)
    dmg = int(dmg * crit_mod)
    dmg = int(dmg * random_frac)
    dmg = int(dmg * stab)
    # 타입 상성은 Fraction으로 누적 후 한 번에 floor
    dmg = int(dmg * type_eff)
    # 기타 보정 (각각 독립 floor)
    dmg = int(dmg * burn_mod)
    dmg = int(dmg * field_mod)
    dmg = int(dmg * atk_ability_mod)
    dmg = int(dmg * def_ability_mod)
    dmg = int(dmg * item_mod)
    dmg = int(dmg * choice_mod)
    dmg = int(dmg * berry_mod)

    # 최소 데미지는 1
    dmg = max(1, dmg)

    return {
        "damage": dmg,
        "is_critical": is_critical,
        "random_roll": float(random_frac),
        "type_eff": type_eff,
        "is_stab": is_stab,
    }


# ──────────────────────────────────────────────
# 행동(Action) 데이터 클래스
# ──────────────────────────────────────────────

@dataclass
class Action:
    """
    한 포켓몬의 한 턴 행동을 나타냅니다.

    kind      : "move"    — 기술 사용
                "change"  — 교체
                "mega"    — 메가진화 (이어서 기술 사용 필요)
    move      : 사용하는 Move 객체 (kind=="move" 또는 mega 후 기술)
    switch_to : 교체 대상 포켓몬 (kind=="change")
    pokemon   : 행동 주체 포켓몬
    is_player : 플레이어 측이면 True
    """
    kind: str                          # "move" | "change" | "mega"
    pokemon: "Pokemon"
    is_player: bool
    move: Optional["Move"] = None
    switch_to: Optional["Pokemon"] = None

    def effective_priority(self) -> int:
        """
        이 행동의 우선도를 반환합니다.

        7세대 우선도 기준:
          교체(change)    : +6
          기술(move)      : Move.priority 값 그대로
          짓궂은마음      : 변화기 우선도 +1
        """
        if self.kind == "change":
            return 6
        if self.move is not None:
            pri = self.move.priority
            # 짓궂은마음 (Prankster): 변화기 우선도 +1
            if (self.pokemon.ability == "짓궂은마음"
                    and self.move.category == MoveCategory.변화):
                pri += 1
            return pri
        return 0


def _effective_speed(pokemon: "Pokemon", battle: "BattleState") -> int:
    """
    배틀 내 실효 스피드를 계산합니다.

    반영 요소:
      - 랭크 보정  (Pokemon.effective_stat 사용)
      - 마비(PAR)  : ×0.5  (7세대 — 6세대까지는 ×0.25)
      - 구애스카프 : ×1.5
      - 일렉트릭필드 + 서핑피카츄 계열 특성 등은 별도 처리 필요 시 확장
    """
    spd = pokemon.effective_stat("S")

    # 마비 패널티 (7세대: ×1/2)
    if pokemon.status == StatusCondition.PAR:
        spd = int(spd * Fraction(1, 2))

    # 구애스카프
    if pokemon.item == "구애스카프":
        spd = int(spd * Fraction(3, 2))

    # 쾌속 특성 (Swift Swim): 비 중 ×2
    if pokemon.ability == "쓱쓱" and battle.weather == Weather.RAIN:
        spd = spd * 2

    # 엽록소 (Chlorophyll): 쾌청 중 ×2
    if pokemon.ability == "엽록소" and battle.weather == Weather.SUNNY:
        spd = spd * 2

    # 모래헤치기 (Sand Rush): 모래바람 중 ×2
    if pokemon.ability == "모래헤치기" and battle.weather == Weather.SANDSTORM:
        spd = spd * 2

    # 눈치우기 (Slush Rush): 싸라기눈 중 ×2
    if pokemon.ability == "눈치우기" and battle.weather == Weather.HAIL:
        spd = spd * 2

    # 일렉트릭필드 + 서지서퍼 (Surge Surfer)
    if pokemon.ability == "서핑테일" and battle.field == Field.ET:
        spd = spd * 2

    # 속보 (Unburden): 아이템이 없을 때 스피드 ×2
    if pokemon.ability == "속보" and pokemon.item is None:
        spd = spd * 2

    # 슬로스타트 (Slow Start): 처음 5턴 스피드 절반
    if pokemon.ability == "슬로스타트" and getattr(pokemon, 'slow_start_counter', 0) < 5:
        spd = spd // 2

    # 탈피 (Shed Skin) — 스피드 관련 없음

    return spd


def determine_turn_order(
    player_action: "Action",
    foe_action: "Action",
    battle: "BattleState",
) -> list["Action"]:
    # 선제공격손톱 (Quick Claw): 20% 확률로 선공 (우선도 무관)
    # 같은 턴에 양쪽 모두 발동 시 원래 우선도로 비교
    player_qc = (player_action.pokemon.item == "선제공격손톱"
                 and random.random() < 0.20)
    foe_qc    = (foe_action.pokemon.item == "선제공격손톱"
                 and random.random() < 0.20)
    if player_qc and not foe_qc:
        return [player_action, foe_action]
    if foe_qc and not player_qc:
        return [foe_action, player_action]
    # 양쪽 모두 발동이거나 없으면 일반 로직으로
    """
    플레이어와 NPC의 행동 우선도·스피드를 비교하여
    이번 턴의 실제 행동 순서 리스트를 반환합니다.

    7세대 우선도 규칙:
      1. 우선도가 높은 쪽이 먼저.
      2. 우선도가 같으면 실효 스피드가 높은 쪽이 먼저.
         - 트릭룸(TR) 활성화 중에는 스피드가 낮은 쪽이 먼저.
      3. 스피드도 같으면 random.choice로 무작위 결정.

    교체 우선도(+6) 처리:
      - 교체는 항상 기술(최대 +5, 퀵어택계 등)보다 먼저 실행됩니다.
      - 양측이 동시에 교체하면 스피드 비교.

    사이코필드(PT) 활성화 중:
      - 땅에 있는 포켓몬을 대상으로 한 선제 기술(priority>0)을 차단합니다.
      (차단 판정 자체는 기술 실행 시점에 처리하며, 여기서는 순서만 결정)

    Parameters
    ----------
    player_action : 플레이어의 행동
    foe_action    : 상대 NPC의 행동
    battle        : 현재 배틀 상태

    Returns
    -------
    [먼저_행동, 나중_행동]  순서의 Action 리스트
    """
    p_pri = player_action.effective_priority()
    f_pri = foe_action.effective_priority()

    # ── 우선도 비교 ────────────────────────────
    if p_pri != f_pri:
        if p_pri > f_pri:
            return [player_action, foe_action]
        else:
            return [foe_action, player_action]

    # ── 우선도 동일 → 스피드 비교 ─────────────
    p_spd = _effective_speed(player_action.pokemon, battle)
    f_spd = _effective_speed(foe_action.pokemon, battle)

    trick_room = battle.is_trick_room()

    if p_spd != f_spd:
        # 트릭룸: 느린 쪽 우선
        player_first = (p_spd > f_spd) if not trick_room else (p_spd < f_spd)
        if player_first:
            return [player_action, foe_action]
        else:
            return [foe_action, player_action]

    # ── 스피드도 동일 → 무작위 ────────────────
    if random.random() < 0.5:
        return [player_action, foe_action]
    else:
        return [foe_action, player_action]


# ══════════════════════════════════════════════
#  메가진화 / Z기술 시스템
# ══════════════════════════════════════════════

# 메가진화 후 종족값 테이블
# key: 포켓몬 이름(한글)  value: {"H":…, "A":…, "B":…, "C":…, "D":…, "S":…}
MEGA_BASE_STATS: dict[str, dict[str, int]] = {
    "이상해꽃":          {"H": 80 , "A": 100, "B": 123, "C": 122, "D": 120, "S": 80 },
    "리자몽X":          {"H": 78 , "A": 130, "B": 111, "C": 130, "D": 85 , "S": 100},
    "리자몽Y":          {"H": 78 , "A": 104, "B": 78 , "C": 159, "D": 115, "S": 100},
    "거북왕":           {"H": 79 , "A": 103, "B": 120, "C": 135, "D": 115, "S": 78 },
    "후딘":            {"H": 55 , "A": 50 , "B": 65 , "C": 175, "D": 105, "S": 150},
    "팬텀":            {"H": 60 , "A": 65 , "B": 80 , "C": 170, "D": 95 , "S": 130},
    "캥카":            {"H": 105, "A": 125, "B": 100, "C": 60 , "D": 100, "S": 100},
    "쁘사이저":          {"H": 65 , "A": 155, "B": 120, "C": 65 , "D": 90 , "S": 105},
    "갸라도스":          {"H": 95 , "A": 155, "B": 109, "C": 70 , "D": 130, "S": 81 },
    "프테라":           {"H": 80 , "A": 135, "B": 85 , "C": 70 , "D": 95 , "S": 150},
    "뮤츠X":           {"H": 106, "A": 190, "B": 100, "C": 154, "D": 100, "S": 130},
    "뮤츠Y":           {"H": 106, "A": 150, "B": 70 , "C": 194, "D": 120, "S": 140},
    "전룡":            {"H": 90 , "A": 95 , "B": 105, "C": 165, "D": 110, "S": 45 },
    "핫삼":            {"H": 70 , "A": 150, "B": 140, "C": 65 , "D": 100, "S": 75 },
    "헤라크로스":         {"H": 80 , "A": 185, "B": 115, "C": 40 , "D": 105, "S": 75 },
    "헬가":            {"H": 75 , "A": 90 , "B": 90 , "C": 140, "D": 90 , "S": 115},
    "마기라스":          {"H": 100, "A": 164, "B": 150, "C": 95 , "D": 120, "S": 71 },
    "번치코":           {"H": 80 , "A": 160, "B": 80 , "C": 130, "D": 80 , "S": 100},
    "가디안":           {"H": 68 , "A": 85 , "B": 65 , "C": 165, "D": 135, "S": 100},
    "입치트":           {"H": 50 , "A": 105, "B": 125, "C": 55 , "D": 95 , "S": 50 },
    "보스로라":          {"H": 70 , "A": 140, "B": 230, "C": 60 , "D": 80 , "S": 50 },
    "요가램":           {"H": 60 , "A": 100, "B": 85 , "C": 80 , "D": 85 , "S": 100},
    "썬더볼트":          {"H": 70 , "A": 75 , "B": 80 , "C": 135, "D": 80 , "S": 135},
    "다크펫":           {"H": 64 , "A": 165, "B": 75 , "C": 93 , "D": 83 , "S": 75 },
    "앱솔":            {"H": 65 , "A": 150, "B": 60 , "C": 115, "D": 60 , "S": 115},
    "한카리아스":         {"H": 108, "A": 170, "B": 115, "C": 120, "D": 95 , "S": 92 },
    "루카리오":          {"H": 70 , "A": 145, "B": 88 , "C": 140, "D": 70 , "S": 112},
    "눈설왕":           {"H": 90 , "A": 132, "B": 105, "C": 132, "D": 105, "S": 30 },
    "라티아스":          {"H": 80 , "A": 100, "B": 120, "C": 140, "D": 150, "S": 110},
    "라티오스":          {"H": 80 , "A": 130, "B": 100, "C": 160, "D": 120, "S": 110},
    "대짱이":           {"H": 100, "A": 150, "B": 110, "C": 95 , "D": 110, "S": 70 },
    "나무킹":           {"H": 70 , "A": 110, "B": 75 , "C": 145, "D": 85 , "S": 145},
    "깜까미":           {"H": 50 , "A": 85 , "B": 125, "C": 85 , "D": 115, "S": 20 },
    "파비코리":          {"H": 75 , "A": 110, "B": 110, "C": 110, "D": 105, "S": 80 },
    "엘레이드":          {"H": 68 , "A": 165, "B": 95 , "C": 65 , "D": 115, "S": 110},
    "다부니":           {"H": 103, "A": 60 , "B": 126, "C": 80 , "D": 126, "S": 50 },
    "샤크니아":          {"H": 70 , "A": 140, "B": 70 , "C": 110, "D": 65 , "S": 105},
    "야도란":           {"H": 95 , "A": 75 , "B": 180, "C": 130, "D": 80 , "S": 30 },
    "강철톤":           {"H": 75 , "A": 125, "B": 230, "C": 55 , "D": 95 , "S": 30 },
    "피죤투":           {"H": 83 , "A": 80 , "B": 80 , "C": 135, "D": 80 , "S": 121},
    "얼음귀신":          {"H": 80 , "A": 120, "B": 80 , "C": 120, "D": 80 , "S": 100},
    "디안시":           {"H": 50 , "A": 160, "B": 110, "C": 160, "D": 110, "S": 110},
    "메타그로스":         {"H": 80 , "A": 145, "B": 150, "C": 105, "D": 110, "S": 110},
    "레쿠쟈":           {"H": 105, "A": 180, "B": 100, "C": 180, "D": 100, "S": 115},
    "폭타":            {"H": 70 , "A": 120, "B": 100, "C": 145, "D": 105, "S": 20 },
    "이어롭":           {"H": 65 , "A": 136, "B": 94 , "C": 54 , "D": 96 , "S": 135},
    "보만다":           {"H": 95 , "A": 145, "B": 130, "C": 120, "D": 90 , "S": 120},
    "독침붕":           {"H": 65 , "A": 150, "B": 40 , "C": 15 , "D": 80 , "S": 145},
}


def apply_mega_evolution(pokemon: "Pokemon", battle_used: bool = False) -> bool:
    """
    메가진화를 수행합니다. 배틀 중 최초 1회만 허용됩니다.

    Parameters
    ----------
    pokemon     : 메가진화할 포켓몬
    battle_used : 이번 배틀에서 이미 메가진화를 사용했으면 True

    Returns
    -------
    True  : 메가진화 성공
    False : 실패 (이미 사용, 메가스톤 없음, 이미 메가진화 상태)

    Side-effects
    ------------
    - pokemon.is_mega = True
    - pokemon.ability ← mega_ability
    - pokemon.types   ← mega_types (있을 경우)
    - pokemon.max_stats 재계산 (MEGA_BASE_STATS 참조)
    - current_hp 비율 보정 (HP 종족값 변화 시)
    """
    if battle_used:
        print(f"[apply_mega_evolution] 이번 배틀에서 이미 메가진화를 사용했습니다.",
              file=sys.stderr)
        sys.exit(1)
    if pokemon.is_mega:
        print(f"[apply_mega_evolution] {pokemon.name}은(는) 이미 메가진화 상태입니다.",
              file=sys.stderr)
        sys.exit(1)
    if not pokemon.mega_ability:
        print(f"[apply_mega_evolution] {pokemon.name}은(는) 메가진화를 할 수 없습니다.",
              file=sys.stderr)
        sys.exit(1)

    # 종족값 교체
    if pokemon.name in MEGA_BASE_STATS:
        old_max_hp = pokemon.max_stats["H"]
        pokemon.base_stats = MEGA_BASE_STATS[pokemon.name]
        pokemon.max_stats  = pokemon._calc_all_stats()
        # HP는 종족값이 바뀌어도 현재 HP 비율을 유지 (내림 처리)
        new_max_hp = pokemon.max_stats["H"]
        if old_max_hp != new_max_hp:
            pokemon.current_hp = max(1, int(pokemon.current_hp * new_max_hp / old_max_hp))

    # 특성·타입 교체 (pokemon.mega_evolve() 내부 로직 활용)
    pokemon.mega_evolve()   # is_mega=True, ability, types 갱신
    return True


# Z기술 위력 테이블 (기술 분류별 기본 위력 → Z기술 위력)
# key: 기술 위력  value: Z기술 위력
_Z_POWER_TABLE_PHYSICAL: dict[int, int] = {
    0: 100, 55: 100, 60: 120, 65: 120, 70: 120, 75: 140,
    80: 160, 85: 160, 90: 175, 95: 180, 100: 180, 110: 185,
    120: 190, 125: 190, 130: 195, 140: 198, 150: 200, 200: 200,
}
_Z_POWER_TABLE_SPECIAL: dict[int, int] = {
    0: 100, 40: 100, 50: 100, 55: 100, 60: 120, 65: 120, 70: 120,
    75: 140, 80: 175, 85: 160, 90: 175, 95: 180, 100: 180, 110: 185,
    120: 190, 130: 195, 140: 198, 145: 200, 150: 200, 185: 200, 200: 200,
}


def get_z_move_power(base_move: "Move") -> int:
    """
    일반 기술의 위력으로부터 Z기술 위력을 반환합니다.
    변화기 Z기술은 위력 0을 반환합니다.
    """
    if base_move.category == MoveCategory.변화:
        return 0
    table = (
        _Z_POWER_TABLE_PHYSICAL
        if base_move.category == MoveCategory.물리
        else _Z_POWER_TABLE_SPECIAL
    )
    # 가장 가까운 하한 키로 검색
    power = base_move.power
    keys = sorted(table.keys())
    result = 100
    for k in keys:
        if power >= k:
            result = table[k]
    return result


# ══════════════════════════════════════════════
#  상태이상 처리 함수
# ══════════════════════════════════════════════

def check_status_before_move(pokemon: "Pokemon") -> dict:
    """
    기술 사용 전 상태이상 체크를 수행합니다.
    (잠듦 / 얼음 / 마비 몸저림 / 혼란 자해)

    Returns
    -------
    dict:
        can_move    : bool   기술을 사용할 수 있으면 True
        event       : str    발생한 이벤트 설명 ("sleep", "frozen", "par_full",
                              "confusion_self_hit", "confusion_snapped_out", "")
        self_damage : int    혼란 자해 데미지 (없으면 0)
    """
    result = {"can_move": True, "event": "", "self_damage": 0}

    # ── 잠듦(SLP) ──────────────────────────────
    if pokemon.status == StatusCondition.SLP:
        if pokemon.sleep_counter <= 0:
            # 잠든 첫 턴 진입: 1~3턴 설정 (이미 설정돼 있지 않으면)
            pokemon.sleep_counter = random.randint(1, 3)
        pokemon.sleep_counter -= 1
        if pokemon.sleep_counter <= 0:
            # 기상
            pokemon.cure_status()
            result["event"] = "sleep_wake"
            result["can_move"] = False   # 기상 턴에는 행동 불가
        else:
            result["event"] = "sleep"
            result["can_move"] = False
        return result

    # ── 얼음(FRZ) ──────────────────────────────
    if pokemon.status == StatusCondition.FRZ:
        # 7세대: 매 턴 20% 확률로 해동
        if random.random() < 0.20:
            pokemon.cure_status()
            result["event"] = "thaw"
            # 해동 턴에는 기술 사용 가능
        else:
            result["event"] = "frozen"
            result["can_move"] = False
        return result

    # ── 마비(PAR) 몸저림 ───────────────────────
    if pokemon.status == StatusCondition.PAR:
        # 7세대: 25% 확률로 행동 불가
        if random.random() < 0.25:
            result["event"] = "par_full"
            result["can_move"] = False
            return result

    # ── 혼란(CNF) ──────────────────────────────
    if VolatileStatus.CNF in pokemon.volatile_statuses:
        pokemon.confusion_counter -= 1
        if pokemon.confusion_counter <= 0:
            pokemon.cure_volatile(VolatileStatus.CNF)
            result["event"] = "confusion_snapped_out"
            # 혼란이 풀린 턴에는 정상 행동
        else:
            # 33% 확률로 자해
            if random.random() < 1 / 3:
                # 자해 데미지: 위력 40 물리 무타입 자신에게 (랭크 무시, 자속 없음)
                # 7세대 혼란 자해 = floor((Lv×2/5+2) × 40 × A / D / 50 + 2)
                # 급소·랜덤·STAB 없음, 랭크 양수 무시(공격), 음수 무시(방어)
                atk = max(pokemon.max_stats["A"],
                          int(pokemon.max_stats["A"] * max(pokemon.rank["A"], 0)
                              * 2 / 2))  # 양수 랭크만 반영
                # 7세대 혼란 자해는 랭크 미반영 (본가 확인값)
                atk = pokemon.max_stats["A"]
                def_ = pokemon.max_stats["B"]
                dmg = int(int(2 * pokemon.level / 5 + 2) * 40 * atk / def_ / 50) + 2
                dmg = max(1, dmg)
                pokemon.take_damage(dmg)
                result["event"] = "confusion_self_hit"
                result["self_damage"] = dmg
                result["can_move"] = False

    return result


def apply_move_secondary_effect(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
    damage_dealt: int,
    battle: "BattleState",
) -> list[str]:
    """
    기술이 명중하고 데미지를 준 직후, 부가효과를 적용합니다.

    처리 내용:
      - 상태이상 부여 (확률 판정)
      - 휘발성 상태이상 부여 (풀죽음 등)
      - 랭크 변화 (공격측/방어측)
      - 반동 데미지
      - 흡수 회복
      - 다단히트는 호출 측에서 반복하여 처리

    Returns
    -------
    발생한 이벤트 문자열 목록 (로그용)
    """
    events: list[str] = []
    eff = move.effect

    # ── 부가효과 발동 확률 판정 ────────────────
    # 하늘의은총: 부가효과 확률 2배
    effective_chance = eff.chance
    if attacker.ability == "하늘의은총" and effective_chance > 0:
        effective_chance = min(100, effective_chance * 2)
    # 우격다짐: 부가효과 제거 → 확률 0으로
    if attacker.ability == "우격다짐":
        effective_chance = 0
    triggered = (effective_chance > 0) and (random.randint(1, 100) <= effective_chance)

    if triggered:
        # 비휘발성 상태이상
        if eff.status is not None:
            defender_grounded = (
                PokemonType.비행 not in defender.types
                and defender.ability not in ("부유",)
            )
            if battle.field == Field.MT and defender_grounded:
                events.append("mist_field_blocked_status")
            else:
                if _can_apply_status(defender, eff.status, battle):
                    if defender.apply_status(eff.status):
                        events.append(f"status_{eff.status.value}")
                        # 루미열매: 바위 타입 반감 (calculate_damage의 berry_mod에서 처리)

        # 휘발성 상태이상
        if eff.volatile is not None:
            if defender.apply_volatile(eff.volatile):
                events.append(f"volatile_{eff.volatile.value}")
                if eff.volatile == VolatileStatus.CNF:
                    # 혼란 지속 턴: 2~5턴
                    defender.confusion_counter = random.randint(2, 5)

        # 랭크 변화
        if eff.stat_changes:
            target = attacker if eff.target == "self" else defender
            for stat, delta in eff.stat_changes.items():
                # 비비드바디: 랭크 하락 무효 + 특공 +2
                if delta < 0 and target.ability == "비비드바디":
                    a2 = target.change_rank("C", +2)
                    if a2: events.append(f"rank_{target.name}_C+{a2}")
                    continue
                actual = target.change_rank(stat, delta)
                if actual != 0:
                    sign = "+" if actual > 0 else ""
                    events.append(f"rank_{target.name}_{stat}_{sign}{actual}")
                    # 오기 (Defiant): 랭크 하락 시 A+2
                    if actual < 0 and target.ability == "오기":
                        a2 = target.change_rank("A", +2)
                        if a2:
                            events.append(f"rank_{target.name}_A+{a2}")

    # ── 풀죽음 (flinch) ─── 부가효과 확률과 독립
    if eff.flinch_chance > 0 and random.randint(1, 100) <= eff.flinch_chance:
        if defender.apply_volatile(VolatileStatus.FLI):
            events.append("flinch")

    # ── 왕의징표석 (King's Rock): 데미지를 주는 기술에 10% 풀죽음 ─
    # 원래 풀죽음 효과가 있는 기술(flinch_chance > 0)은 제외
    if (attacker.item == "왕의징표석"
            and damage_dealt > 0
            and eff.flinch_chance == 0
            and move.category != MoveCategory.변화
            and random.random() < 0.10):
        if defender.apply_volatile(VolatileStatus.FLI):
            events.append("kings_rock_flinch")

    # ── 반동 데미지 ────────────────────────────
    if eff.recoil_ratio > 0 and damage_dealt > 0:
        # 돌머리(Rock Head)/매직가드: 반동 무효
        if attacker.ability not in ("돌머리", "매직가드"):
            recoil = max(1, int(damage_dealt * eff.recoil_ratio))
            attacker.take_damage(recoil)
            events.append(f"recoil_{recoil}")

    # ── 흡수 회복 ──────────────────────────────
    if eff.drain_ratio > 0 and damage_dealt > 0:
        drain = max(1, int(damage_dealt * eff.drain_ratio))
        # 큰뿌리: 흡수량 1.3배
        if attacker.item == "큰뿌리":
            drain = int(drain * 1.3)
        # 액체흡수(Liquid Ooze) 특성이면 오히려 데미지
        if defender.ability == "해감액":
            attacker.take_damage(drain)
            events.append(f"liquid_ooze_{drain}")
        else:
            healed = attacker.heal(drain)
            events.append(f"drain_{healed}")

    # ── 조개껍질방울 (Shell Bell): 입힌 데미지의 1/8 회복 ─
    if attacker.item == "조개껍질방울" and damage_dealt > 0:
        healed = attacker.heal(max(1, damage_dealt // 8))
        events.append(f"shell_bell_{healed}")

    return events


def _can_apply_status(
    target: "Pokemon",
    status: StatusCondition,
    battle: "BattleState",
) -> bool:
    """
    상태이상을 부여할 수 있는지 사전 조건을 확인합니다.

    불가 조건:
      - 이미 상태이상 보유
      - 타입 면역 (불꽃→화상, 독/강철→독/맹독, 전기→마비, 얼음→얼음)
      - 특성 면역 (마그마의무장→화상, 수포→화상, 자연회복은 교체 시 회복이므로 부여 가능)
      - 미스트필드 (호출 측에서 처리)
      - 강철 타입은 독/맹독 면역
    """
    if target.status is not None:
        return False

    types = target.types
    ability = target.ability

    if status in (StatusCondition.PSN, StatusCondition.TOX):
        if PokemonType.독 in types or PokemonType.강철 in types:
            return False
        if ability in ("면역",):  # immunity
            return False

    if status == StatusCondition.BRN:
        if PokemonType.불꽃 in types:
            return False
        if ability in ("마그마의무장", "수포", "수의베일"):
            return False

    if status == StatusCondition.PAR:
        # 7세대: 전기 타입은 마비 면역
        if PokemonType.전기 in types:
            return False
        if ability == "유연":
            return False

    if status == StatusCondition.FRZ:
        if PokemonType.얼음 in types:
            return False
        # 쾌청 중 얼음 불가
        if battle.weather == Weather.SUNNY:
            return False
        if ability == "마그마의무장":
            return False

    if status == StatusCondition.SLP:
        if ability in ("불면", "트레이스", "스위트베일", "화신"):
            return False
        if battle.field == Field.ET:
            grounded = (
                PokemonType.비행 not in target.types
                and target.ability not in ("부유",)
            )
            if grounded:
                return False

    # VolatileStatus.CNF(혼란): 마이페이스 면역
    # 이 함수는 StatusCondition만 처리하므로 혼란은 apply_volatile 시 별도 처리 필요

    return True


def apply_end_of_turn_damage(pokemon: "Pokemon", battle: "BattleState") -> list[str]:
    """
    턴 종료 시 포켓몬이 받는 지속 데미지를 처리합니다.

    처리 순서 (7세대 기준):
      1. 날씨 (싸라기눈/모래바람)
      2. 독/맹독
      3. 화상
      4. 조이기(BND)
      5. 씨뿌리기(미구현 플래그 있으면 처리)

    Returns
    -------
    발생한 이벤트 문자열 목록
    """
    events: list[str] = []
    if pokemon.is_fainted:
        return events

    max_hp = pokemon.max_stats["H"]
    ability = pokemon.ability
    has_magic_guard = (ability == "매직가드")

    # ── 화염구슬: 매 턴 화상 부여 ─────────────
    if pokemon.item == "화염구슬" and pokemon.status is None:
        if _can_apply_status(pokemon, StatusCondition.BRN, battle):
            pokemon.apply_status(StatusCondition.BRN)
            events.append("flame_orb_brn")

    # ── 탈피 (Shed Skin): 30% 상태이상 회복 ───
    if ability == "탈피" and pokemon.status is not None:
        if random.random() < 0.30:
            pokemon.cure_status()
            events.append("shed_skin_heal")

    # ── 슬로스타트 카운터 증가 ────────────────
    if ability == "슬로스타트":
        pokemon.slow_start_counter += 1
        if pokemon.slow_start_counter >= 5:
            events.append("slow_start_ended")

    # ── 1. 날씨 데미지 ─────────────────────────
    if battle.weather == Weather.SANDSTORM:
        # 바위/강철/땅 타입, 모래숨기·모래의힘·모래날림 특성은 면역
        immune_types  = {PokemonType.바위, PokemonType.강철, PokemonType.땅}
        immune_abil   = {"모래숨기", "모래의힘", "모래날림", "방진"}
        if not (any(t in pokemon.types for t in immune_types)
                or pokemon.ability in immune_abil
                or has_magic_guard):
            dmg = max(1, max_hp // 16)
            pokemon.take_damage(dmg)
            events.append(f"sandstorm_damage_{dmg}")

    if battle.weather == Weather.HAIL:
        # 얼음 타입 면역
        if (PokemonType.얼음 not in pokemon.types
                and pokemon.ability != "아이스바디"
                and not has_magic_guard):
            dmg = max(1, max_hp // 16)
            pokemon.take_damage(dmg)
            events.append(f"hail_damage_{dmg}")
        # 아이스바디: 싸라기눈 중 HP 1/16 회복
        if pokemon.ability == "아이스바디" and pokemon.current_hp < max_hp:
            healed = pokemon.heal(max(1, max_hp // 16))
            events.append(f"icebody_heal_{healed}")

    # ── 2. 독(PSN) ─────────────────────────────
    if pokemon.status == StatusCondition.PSN and not has_magic_guard:
        dmg = max(1, max_hp // 8)
        pokemon.take_damage(dmg)
        events.append(f"psn_damage_{dmg}")

    # ── 3. 맹독(TOX) ───────────────────────────
    elif pokemon.status == StatusCondition.TOX and not has_magic_guard:
        dmg = max(1, int(max_hp * pokemon.toxic_counter / 16))
        pokemon.take_damage(dmg)
        events.append(f"tox_damage_{dmg}_counter{pokemon.toxic_counter}")
        pokemon.toxic_counter = min(pokemon.toxic_counter + 1, 15)

    # ── 4. 화상(BRN) ───────────────────────────
    if pokemon.status == StatusCondition.BRN and not has_magic_guard:
        # 화상: 최대 HP의 1/16 (7세대)
        # 근성 특성이면 데미지 여전히 받음 (공격 보정만 됨)
        dmg = max(1, max_hp // 16)
        pokemon.take_damage(dmg)
        events.append(f"brn_damage_{dmg}")

    # ── 5. 조이기(BND) ─────────────────────────
    if VolatileStatus.BND in pokemon.volatile_statuses:
        dmg = max(1, max_hp // 8)
        # 덩굴채찍 아이템 장착 시 1/6
        pokemon.take_damage(dmg)
        events.append(f"bind_damage_{dmg}")

    # ── 그래스필드 회복 ────────────────────────
    if battle.field == Field.GT:
        grounded = (
            PokemonType.비행 not in pokemon.types
            and pokemon.ability not in ("부유",)
        )
        if grounded and pokemon.current_hp < max_hp and not pokemon.is_fainted:
            healed = pokemon.heal(max(1, max_hp // 16))
            events.append(f"grassy_terrain_heal_{healed}")

    # ── 진화의휘석: 방어/특방 ×1.5 → _ability_def_modifier에서 처리, 여기서는 없음

    # ── 남은열매 (Leftovers) ───────────────────
    if pokemon.item == "먹다남은음식":
        if pokemon.current_hp < max_hp:
            healed = pokemon.heal(max(1, max_hp // 16))
            events.append(f"leftovers_heal_{healed}")

    # ── 복분열매: 화상 상태이상 치료 ──────────────
    # 화상 데미지를 받은 직후 발동 (화상 데미지 처리 이후)
    if (pokemon.item == "복분열매"
            and pokemon.status == StatusCondition.BRN
            and not pokemon.is_fainted):
        pokemon.cure_status()
        pokemon.item = None
        events.append("rawst_berry_heal_brn")

    # ── 무사태평향로: 명중률 감소 → 명중 판정에서 처리

    # ── 왕의징표석: 물리 접촉 10% 풀죽음 → apply_contact_ability에서 처리

    # ── 검은진흙 (Black Sludge) ────────────────
    # 독 타입: 매 턴 HP 1/16 회복 / 비독 타입: 매 턴 HP 1/8 데미지
    if pokemon.item == "검은진흙" and not pokemon.is_fainted:
        if PokemonType.독 in pokemon.types:
            if pokemon.current_hp < max_hp:
                healed = pokemon.heal(max(1, max_hp // 16))
                events.append(f"black_sludge_heal_{healed}")
        elif not has_magic_guard:
            dmg = max(1, max_hp // 8)
            pokemon.take_damage(dmg)
            events.append(f"black_sludge_damage_{dmg}")

    # ── 젖은접시 (Hydration/Wet Rock): 비 중 HP 회복 ─
    if pokemon.ability == "젖은접시" and battle.weather == Weather.RAIN:
        if pokemon.current_hp < max_hp and not pokemon.is_fainted:
            healed = pokemon.heal(max(1, max_hp // 16))
            events.append(f"wet_rock_heal_{healed}")

    # ── 촉촉바디: 비 중 상태이상 회복 ─────────
    if pokemon.ability == "촉촉바디" and battle.weather == Weather.RAIN:
        if pokemon.status is not None:
            pokemon.cure_status()
            events.append("rain_dish_heal_status")

    # ── 독가시/모래 특성은 접촉 시 처리 ────────

    return events


# ══════════════════════════════════════════════
#  변화기(Status Move) 처리
# ══════════════════════════════════════════════

def apply_stat_move(
    user: "Pokemon",
    target: "Pokemon",
    move: "Move",
    battle: "BattleState",
) -> list[str]:
    """
    변화기를 사용했을 때의 효과를 적용합니다.

    지원 기술 목록 (7세대 기준 주요 기술):
      랭크 변화: 칼춤, 용의춤, 나쁜음모, 특수방어올리기, 껍질깨기,
                 방어강화, 특방강화, 도발 등의 랭크 변화 계열
      HP 회복:   HP회복, 달빛, 아침햇살, 합성, 자기재생
      보호계:    방어(방어 플래그), 칼막기
      대타출동
      맹독
      앙코르
      기타 필드/날씨 기술

    Returns
    -------
    이벤트 문자열 목록
    """
    events: list[str] = []
    name = move.name

    # ── 매직미러 (Magic Bounce): 상대방 향한 변화기 반사 ───
    if (move.effect.target != "self"
            and target.ability == "매직미러"
            and name not in ("중력", "트릭룸", "매직룸", "원더룸")):
        events.append("magic_bounce_reflected")
        return apply_stat_move(target, user, move, battle)

    # ── 랭크 직접 변화 기술 ────────────────────
    # 효과가 MoveEffect.stat_changes에 정의된 경우 (부가효과 확률 100%로 처리)
    if move.effect.stat_changes and move.effect.target in ("self", "foe"):
        t = user if move.effect.target == "self" else target
        for stat, delta in move.effect.stat_changes.items():
            # 비비드바디: 랭크 하락 → 무효 + 특공 +2
            if delta < 0 and t.ability == "비비드바디":
                a2 = t.change_rank("C", +2)
                if a2: events.append(f"rank_{t.name}_C+{a2}")
                continue
            actual = t.change_rank(stat, delta)
            if actual != 0:
                sign = "+" if actual > 0 else ""
                events.append(f"rank_{t.name}_{stat}_{sign}{actual}")
                # 오기: 랭크 하락 시 A+2
                if actual < 0 and t.ability == "오기":
                    a2 = t.change_rank("A", +2)
                    if a2: events.append(f"rank_{t.name}_A+{a2}")
        return events

    # ── HP 회복계 기술 ─────────────────────────
    if name in ("HP회복", "달의불빛", "아침햇살", "광합성", "잠자기", "날개쉬기",
                "초승달춤", "태만함", "알낳기", "우유마시기"):
        heal_ratio = _recover_ratio(user, move, battle)
        healed = user.heal(max(1, int(user.max_stats["H"] * heal_ratio)))
        events.append(f"recover_{healed}")
        return events

    # ── 방어계 기술 ────────────────────────────
    if name in ("방어", "판별", "토치카", "니들가드"):
        user.protect_active = True
        events.append("protect")
        return events

    if name == "킹실드":
        user.protect_active = True
        events.append("protect")
        return events

    # ── 대타출동 ───────────────────────────────
    if name == "대타출동":
        cost = user.max_stats["H"] // 4
        if user.current_hp <= cost:
            events.append("substitute_failed_no_hp")
            return events
        if user.substitute_hp > 0:
            events.append("substitute_failed_already")
            return events
        user.take_damage(cost)
        user.substitute_hp = cost
        events.append(f"substitute_created_{cost}")
        return events

    # ── 맹독 ───────────────────────────────────
    if name == "맹독":
        if _can_apply_status(target, StatusCondition.TOX, battle):
            target.apply_status(StatusCondition.TOX)
            events.append("tox_applied")
        else:
            events.append("tox_failed")
        return events

    # ── 앙코르 ─────────────────────────────────
    if name == "앵콜":
        if target.last_used_move is not None and target.locked_move is None:
            target.locked_move = target.last_used_move
            target.encore_counter = 3   # 3턴 지속
            events.append(f"encore_{target.last_used_move}")
        else:
            events.append("encore_failed")
        return events

    # ── 도발 ───────────────────────────────────
    if name == "도발":
        # 도발: 3턴간 변화기 사용 불가
        # 별도 플래그 taunt_counter 필요 → 임시로 volatile 기록 생략, 이벤트만 발행
        events.append("taunt_applied")
        return events

    # ── 중력 ───────────────────────────────────
    if name == "중력":
        battle.set_room(RoomEffect.GR, turns=5)
        events.append("gravity_started")
        return events

    # ── 트릭룸 ─────────────────────────────────
    if name == "트릭룸":
        battle.set_room(RoomEffect.TR, turns=5)
        events.append("trick_room_toggled")
        return events

    # ── 날씨 기술 ──────────────────────────────
    _weather_moves: dict[str, Weather] = {
        "쾌청": Weather.SUNNY, "맑게개다": Weather.SUNNY,
        "비바라기": Weather.RAIN,
        "모래바람": Weather.SANDSTORM,
        "싸라기눈": Weather.HAIL,
    }
    if name in _weather_moves:
        turns = 8 if user.item in ("열탄바위", "습기바위", "매끄러운바위", "얼음바위") else 5
        battle.set_weather(_weather_moves[name], turns=turns)
        events.append(f"weather_{_weather_moves[name].value}_set")
        return events

    # ── 필드 기술 ──────────────────────────────
    _field_moves: dict[str, Field] = {
        "일렉트릭필드": Field.ET,
        "그래스필드":   Field.GT,
        "미스트필드":   Field.MT,
        "사이코필드":   Field.PT,
    }
    if name in _field_moves:
        battle.set_field(_field_moves[name], turns=5)
        events.append(f"field_{_field_moves[name].value}_set")
        return events

    # ── 매직룸 / 원더룸 ────────────────────────
    if name == "매직룸":
        battle.set_room(RoomEffect.MR, turns=5)
        events.append("magic_room_toggled")
        return events
    if name == "원더룸":
        battle.set_room(RoomEffect.WR, turns=5)
        events.append("wonder_room_toggled")
        return events

    # ── 스텔스록 / 압정뿌리기 등 장판기 ─────────
    if name == "스텔스록":
        events.append("stealth_rock_set")   # 인터랙터는 장판 HP 계산 별도 처리
        return events
    if name in ("압정뿌리기", "독압정"):
        events.append(f"spike_set_{name}")
        return events

    # ── 미분류 변화기: MoveEffect의 stat_changes 처리 ──
    # (위에서 처리됐어야 하나 stat_changes가 없는 변화기)
    events.append(f"status_move_unhandled_{name}")
    return events


def _recover_ratio(user: "Pokemon", move: "Move", battle: "BattleState") -> float:
    """
    회복기의 회복 비율을 날씨·특성에 따라 반환합니다.
    기본: 0.5 (최대 HP의 50%)
    아침햇살/달빛/합성 계열은 날씨 영향 받음.
    """
    weather_sensitive = {"아침햇살", "달의불빛", "광합성"}
    if move.name in weather_sensitive:
        if battle.weather == Weather.SUNNY:
            return 2 / 3
        if battle.weather in (Weather.RAIN, Weather.SANDSTORM, Weather.HAIL):
            return 0.25
    return 0.5


# ══════════════════════════════════════════════
#  특성(Ability) 발동 처리
# ══════════════════════════════════════════════

def apply_entry_ability(
    pokemon: "Pokemon",
    opponent: "Pokemon",
    battle: "BattleState",
) -> list[str]:
    """
    포켓몬이 배틀 필드에 등장할 때 발동하는 특성을 처리합니다.

    대상 특성:
      위협(Intimidate)      : 상대 공격 -1
      다운로드(Download)    : 상대 방어 vs 특방 비교 → 공격/특공 +1
      위압감(Pressure)      : 효과 없음(PP 추가 소모, 공지용 이벤트만 발행)
      가속(Speed Boost)     : 등장 시 스피드 +1 (※ 가속은 턴 종료 시이나 등장 턴 예외 없음)
      추적(Trace)            : 상대 특성 복사 (복사 이벤트만 발행)
      모래날리기(Sand Stream): 모래바람 발생
      가뭄(Drought)         : 쾌청 발생
      물의흡수 계열은 피해 무효 → 데미지 계산 시 처리
      사이코메이커(Psychic Surge): 사이코필드 발생
      미스트메이커(Misty Surge): 미스트필드 발생
      일렉트릭메이커(Electric Surge): 일렉트릭필드 발생
      그래스메이커(Grassy Surge): 그래스필드 발생
      까칠한피부(Rough Skin) / 철가시(Iron Barbs): 등장 시 효과 없음(접촉 시 처리)
      자연치유(Natural Cure): 교체 시 상태이상 회복 → reset_battle_volatile 아닌 별도 처리
      재생력(Regenerator)   : 교체 시 HP 1/3 회복 → 교체 시점에 별도 처리

    Returns
    -------
    이벤트 문자열 목록
    """
    events: list[str] = []
    ability = pokemon.ability

    # ── 위협 (Intimidate) ──────────────────────
    if ability == "위협":
        # 위협 무효 특성: 클리어바디, 하얀연기, 메탈프로텍트, 괴력집게, 정신력
        # (과식·큰뿌리는 위협 무효가 아님)
        _immune_abilities = {"클리어바디", "하얀연기", "메탈프로텍트", "괴력집게", "정신력"}
        if opponent.ability not in _immune_abilities:
            actual = opponent.change_rank("A", -1)
            if actual != 0:
                events.append(f"intimidate_{opponent.name}_A{actual}")
        else:
            events.append(f"intimidate_blocked_{opponent.ability}")

    # ── 다운로드 (Download) ────────────────────
    elif ability == "다운로드":
        # 상대의 방어 vs 특방 실수치 비교 (랭크 무시)
        # 방어 ≤ 특방 → 공격 +1 / 방어 > 특방 → 특공 +1
        if opponent.max_stats["B"] <= opponent.max_stats["D"]:
            actual = pokemon.change_rank("A", +1)
            events.append(f"download_{pokemon.name}_A+{actual}")
        else:
            actual = pokemon.change_rank("C", +1)
            events.append(f"download_{pokemon.name}_C+{actual}")

    # ── 날씨·필드 발동 특성 ────────────────────
    elif ability == "모래날림":
        battle.set_weather(Weather.SANDSTORM, turns=5)
        events.append("ability_sandstream")
    elif ability == "가뭄":
        battle.set_weather(Weather.SUNNY, turns=5)
        events.append("ability_drought")
    elif ability == "잔비":
        battle.set_weather(Weather.RAIN, turns=5)
        events.append("ability_drizzle")
    elif ability == "눈퍼뜨리기":
        battle.set_weather(Weather.HAIL, turns=5)
        events.append("ability_snowwarning")
    elif ability == "사이코메이커":
        battle.set_field(Field.PT, turns=5)
        events.append("ability_psychic_surge")
    elif ability == "미스트메이커":
        battle.set_field(Field.MT, turns=5)
        events.append("ability_misty_surge")
    elif ability == "일렉트릭메이커":
        battle.set_field(Field.ET, turns=5)
        events.append("ability_electric_surge")
    elif ability == "그래스메이커":
        battle.set_field(Field.GT, turns=5)
        events.append("ability_grassy_surge")

    # ── 위압감 (Pressure) ──────────────────────
    elif ability == "프레셔":
        events.append(f"pressure_{pokemon.name}")

    # ── 추적 (Trace) ───────────────────────────
    elif ability == "추적":
        # 복사 불가 특성 제외
        _no_trace = {
            "트레이스", "기분파", "일루전", "멀티타입", "AR시스템",
            "배틀스위치", "스웜체인지", "어군", "절대안깸", "달마모드",
        }
        if opponent.ability not in _no_trace:
            pokemon.ability = opponent.ability
            events.append(f"trace_copied_{opponent.ability}")

    # ── 자연치유: 교체 시 처리
    # ── 재생력: 교체 시 처리

    # ── 강철술사 (Steelworker): 강철 기술 ×1.5 → atk_modifier에서 처리
    # ── 불굴의마음 (Justified): 악 기술 맞으면 A+1 → apply_move_secondary에서 처리
    # ── 자기과신 (Moxie): 쓰러뜨리면 A+1 → 기절 처리 후 별도 호출
    # ── 정의의마음 (Justice Heart): 강철/독 쓰러뜨리면 A+1 → 기절 처리 후
    # ── 오기 (Defiant): 랭크 하락 시 A+2 → change_rank 시 처리
    # ── 짓궂은마음 (Prankster): 변화기 우선도 +1 → Action.effective_priority에서 처리
    # ── 리밋실드 (Shields Down): HP 만빵 시 B+1
    if ability == "리밋실드" and pokemon.current_hp == pokemon.max_stats["H"]:
        actual = pokemon.change_rank("B", +1)
        if actual:
            events.append(f"limitshield_{pokemon.name}_B+{actual}")

    # ── 위험예지 (Wonder Guard): 효과 없거나 ×1 이하 기술만 막음 → def_modifier에서 처리
    # ── 매직미러 (Magic Bounce): 변화기 반사 → apply_stat_move에서 처리
    # ── 방탄 (Bulletproof): 일부 변화/공격기 무효 → _execute_move에서 처리

    return events


def apply_switch_out_ability(pokemon: "Pokemon") -> list[str]:
    """
    포켓몬이 교체되어 나올 때(switch-out) 발동하는 특성을 처리합니다.

    대상 특성:
      자연치유(Natural Cure) : 상태이상 회복
      재생력(Regenerator)    : HP 1/3 회복
    """
    events: list[str] = []

    if pokemon.ability == "자연회복" and pokemon.status is not None:
        pokemon.cure_status()
        events.append("natural_cure_healed")

    if pokemon.ability == "재생력":
        healed = pokemon.heal(max(1, pokemon.max_stats["H"] // 3))
        events.append(f"regenerator_healed_{healed}")

    return events


def apply_contact_ability(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
) -> list[str]:
    """
    접촉 기술 명중 후 발동하는 특성(방어측)을 처리합니다.

    대상 특성:
      까칠한피부(Rough Skin) / 철가시(Iron Barbs): 공격측 HP 1/8 반동
      독가시(Poison Point)                        : 30% 확률로 독
      화염몸통(Flame Body)                        : 30% 확률로 화상
      정전기(Static)                              : 30% 확률로 마비
      효과음(Effect Spore)                        : 10% 독, 10% 마비, 10% 잠듦
    """
    events: list[str] = []
    if not move.contact:
        return events

    ability = defender.ability

    if ability in ("까칠한피부", "철가시"):
        dmg = max(1, attacker.max_stats["H"] // 8)
        attacker.take_damage(dmg)
        events.append(f"{ability}_recoil_{dmg}")

    elif ability == "독가시":
        if random.random() < 0.30 and _can_apply_status(attacker, StatusCondition.PSN, BattleState()):
            attacker.apply_status(StatusCondition.PSN)
            events.append("poison_point_psn")

    elif ability == "불꽃몸":
        if random.random() < 0.30 and _can_apply_status(attacker, StatusCondition.BRN, BattleState()):
            attacker.apply_status(StatusCondition.BRN)
            events.append("flame_body_brn")

    elif ability == "정전기":
        if random.random() < 0.30 and _can_apply_status(attacker, StatusCondition.PAR, BattleState()):
            attacker.apply_status(StatusCondition.PAR)
            events.append("static_par")

    elif ability == "포자":
        roll = random.randint(1, 10)
        if roll <= 1:
            if _can_apply_status(attacker, StatusCondition.PSN, BattleState()):
                attacker.apply_status(StatusCondition.PSN)
                events.append("effect_spore_psn")
        elif roll <= 2:
            if _can_apply_status(attacker, StatusCondition.PAR, BattleState()):
                attacker.apply_status(StatusCondition.PAR)
                events.append("effect_spore_par")
        elif roll <= 3:
            if _can_apply_status(attacker, StatusCondition.SLP, BattleState()):
                attacker.apply_status(StatusCondition.SLP)
                events.append("effect_spore_slp")

    # ── 저주받은바디 (Cursed Body): 30% 사슬묶기(Disable) ─
    # 접촉한 기술을 4턴간 사용 불가로 만듦 (앙코르와 반대)
    if ability == "저주받은바디" and random.random() < 0.30:
        if attacker.disabled_move is None and attacker.last_used_move:
            attacker.disabled_move = attacker.last_used_move
            attacker.disable_counter = 4
            events.append(f"cursed_body_disable_{attacker.last_used_move}")

    # ── 나쁜손버릇 (Pickpocket): 접촉 시 상대 아이템 훔침 ─
    if ability == "나쁜손버릇" and defender.item is None and attacker.item is not None:
        defender.item = attacker.item
        attacker.item = None
        events.append(f"pickpocket_stolen")

    # ── 울퉁불퉁멧 (Rocky Helmet): 접촉 시 상대 HP 1/6 데미지 ─
    if defender.item == "울퉁불퉁멧":
        dmg = max(1, attacker.max_stats["H"] // 6)
        attacker.take_damage(dmg)
        events.append(f"rocky_helmet_{dmg}")

    # ── 왕의징표석: apply_move_secondary_effect에서 처리 ───

    # ── 축전 (Volt Absorb): 전기 접촉 기술 맞으면 특공 +1 (본래는 흡수이나 7세대에 없음)
    # ── 피뢰침 (Lightning Rod): 전기 기술 무효 → 명중 판정 전 처리
    # ── 발광 (Flash Fire): 불꽃 기술 무효 → 명중 판정 전 처리
    # ── 초식 (Sap Sipper): 풀 기술 무효 → 명중 판정 전 처리

    return events


def apply_turn_start_ability(pokemon: "Pokemon", battle: "BattleState") -> list[str]:
    """
    턴 시작 시(자신 행동 전) 발동하는 특성을 처리합니다.

    대상:
      속도부스트(Speed Boost) : 스피드 +1  (첫 출전 턴 제외)
      나쁜꿈(Bad Dreams)      : 상대방 잠듦 데미지 (상대 참조 필요 → 호출 측에서 처리)
      모래의힘(Sand Force)    : 데미지 보정 (calculate_damage에서 처리)
    """
    events: list[str] = []

    if pokemon.ability == "가속":
        actual = pokemon.change_rank("S", +1)
        if actual:
            events.append(f"speed_boost_S+{actual}")

    return events


# ══════════════════════════════════════════════
#  Move 속성 확장: is_punch 플래그 및 Z기술 헬퍼
# ══════════════════════════════════════════════

# 7세대 기준 펀치 기술 목록 (철주먹 보정 대상)
PUNCH_MOVES: set[str] = {
    # 7세대 기준 철주먹(Iron Fist) 보정 대상 펀치 기술
    "불꽃펀치", "냉동펀치", "번개펀치", "섀도펀치", "불릿펀치",
    "메가톤펀치", "해머암", "더스트슈트", "코멧펀치", "스카이업퍼",
    "드레인펀치", "마하펀치", "폭발펀치", "힘껏펀치",
}

# 7세대 기준 물기 기술 목록 (옹골찬턱 보정 대상)
BITE_MOVES: set[str] = {
    "벌레먹음",     # bug-bite
    "깨물어부수기", # crunch
    "불꽃엄니",     # fire-fang
    "얼음엄니",     # ice-fang
    "번개엄니",     # thunder-fang
    "독엄니",       # poison-fang
    "다크홀",       # dark-void (7세대까지 존재)
    "필살앞니",     # hyper-fang
    "껍질끼우기",   # clamp
}

# 7세대 기준 소리 기술 목록 (방음(Soundproof) 특성 무효 대상)
SOUND_MOVES: set[str] = {
    "노래하기",         # sing
    "초음파",           # supersonic
    "돌림노래",         # round
    "금속음",           # metal-sound
    "쥐어짜기",         # wring-out
    "울부짖기",         # roar
    "벌레의야단법석",   # bug-buzz
    "에코보이스",       # echoed-voice
    "부르짖기",         # noble-roar         # dragon-rage (7세대까지 소리기술 아님; 실수 제거)
    "하이퍼보이스",     # hyper-voice
           # charge-beam (소리기술 아님; 실수 제거 — 하단 주석 참조)         # sketch (소리기술 아님; 목록에서 제거해도 무방)
    # ※ 용의분노·차지빔·스케치는 소리기술이 아님 — 위에 남긴 것은 기존 코드 호환을 위함
}

# 7세대 기준 파동 기술 목록 (메가런처(Mega Launcher) 보정 대상)
PULSE_MOVES: set[str] = {
    "용의파동",     # dragon-pulse
    "악의파동",     # dark-pulse
    "물의파동",     # water-pulse
    "오로라빔",     # aurora-beam
    "기합구슬",     # focus-blast
    "치유파동",     # heal-pulse
}


def _apply_ability_atk_modifier_extended(
    attacker: "Pokemon",
    defender: "Pokemon",
    move: "Move",
    battle: "BattleState",
) -> Fraction:
    """
    _ability_atk_modifier의 확장판: 추가 특성 보정을 반영합니다.
    기존 함수와 결과를 곱해서 사용합니다.
    """
    ability = attacker.ability
    name    = move.name
    mtype   = move.type_

    # 강한턱 (Strong Jaw): 물기 기술 ×1.5
    if ability == "옹골찬턱" and name in BITE_MOVES:
        return Fraction(3, 2)

    # 철주먹 (Iron Fist): 펀치 기술 ×1.2
    if ability == "철주먹" and name in PUNCH_MOVES:
        return Fraction(6, 5)

    # 메가런처 (Mega Launcher): 파동 기술 ×1.5
    if ability == "메가런처" and name in PULSE_MOVES:
        return Fraction(3, 2)

    # 수포 (Water Bubble): 물 공격 ×2
    if ability == "수포" and mtype == PokemonType.물:
        return Fraction(2)

    # 독폭탄 (Corrosion): 독/맹독을 강철·독 타입에도 부여 가능 → 판정 함수에서 처리

    return Fraction(1)


# ──────────────────────────────────────────────
# 동작 확인 (직접 실행 시)
# ──────────────────────────────────────────────

##### battle classes 파일의 끝

# ── 데이터 파일 경로 ─────────────────────────────────────
# interactor.py 위치 기준으로 상대 경로 탐색
# 우선순위: 1) 환경변수, 2) 프로젝트 디렉터리, 3) 현재 디렉터리
def _find_file(candidates: list[str]) -> str:
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[-1]   # 없으면 마지막 경로 반환 (오류는 런타임에 발생)

# POKEMON_CSV = _find_file([
#     os.environ.get("POKEMON_CSV", ""),
#     "/mnt/project/pokemon.csv",
#     os.path.join(_THIS_DIR, "..", "project", "pokemon.csv"),
#     os.path.join(_THIS_DIR, "pokemon.csv"),
# ])

# TRANS_CSV = _find_file([
#     os.environ.get("TRANS_CSV", ""),
#     "/mnt/user-data/uploads/pokemon_translation_table.csv",
#     os.path.join(_THIS_DIR, "..", "user-data", "uploads",
#                  "pokemon_translation_table.csv"),
# ])

# ══════════════════════════════════════════════════════════
#  내장 기술 데이터베이스  (7세대 이하 주요 기술)
#  네트워크 비활성 환경에서 PokeAPI 대신 사용. 
#############################################################################################################################################################
# ══════════════════════════════════════════════════════════
# fmt: (type, category, power, accuracy, priority, pp, contact,
#        effect_chance, status, volatile, stat_changes, target,
#        flinch_chance, recoil_ratio, drain_ratio)
_OLD_MDB: dict[str, tuple] = {
    # ── 노말 ─────────────────────────────────────────────
    "막치기":          ("노말", "물리", 40, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "연속뺨치기":        ("노말", "물리", 15, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "연속펀치":         ("노말", "물리", 18, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "메가톤펀치":        ("노말", "물리", 80, 85, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "고양이돈받기":       ("노말", "물리", 40, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "할퀴기":          ("노말", "물리", 40, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "찝기":           ("노말", "물리", 55, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "가위자르기":        ("노말", "물리", 0, 30, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "칼바람":          ("노말", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "칼춤":           ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 2}, "self", 0, 0, 0),
    "풀베기":          ("노말", "물리", 50, 95, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "날려버리기":        ("노말", "변화", 0, None, -6, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "조이기":          ("노말", "물리", 15, 85, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "힘껏치기":         ("노말", "물리", 80, 75, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "짓밟기":          ("노말", "물리", 65, 100, 0, 20, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "메가톤킥":         ("노말", "물리", 120, 75, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "박치기":          ("노말", "물리", 70, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "뿔찌르기":         ("노말", "물리", 65, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마구찌르기":        ("노말", "물리", 15, 85, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "뿔드릴":          ("노말", "물리", 0, 30, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "몸통박치기":        ("노말", "물리", 40, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "누르기":          ("노말", "물리", 85, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "김밥말이":         ("노말", "물리", 15, 90, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "돌진":           ("노말", "물리", 90, 85, 0, 20, False, 0, None, None, {}, "foe", 0, 1/4, 0),
    "난동부리기":        ("노말", "물리", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "이판사판태클":       ("노말", "물리", 120, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 1/3, 0),
    "꼬리흔들기":        ("노말", "변화", 0, 100, 0, 30, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "째려보기":         ("노말", "변화", 0, 100, 0, 30, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "울음소리":         ("노말", "변화", 0, 100, 0, 40, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "울부짖기":         ("노말", "변화", 0, None, -6, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "노래하기":         ("노말", "변화", 0, 55, 0, 15, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "초음파":          ("노말", "변화", 0, 55, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "소닉붐":          ("노말", "특수", 0, 90, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사슬묶기":         ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파괴광선":         ("노말", "특수", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "괴력":           ("노말", "물리", 80, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "성장":           ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 1, "C": 1}, "self", 0, 0, 0),
    "전광석화":         ("노말", "물리", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "분노":           ("노말", "물리", 20, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "흉내내기":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "싫은소리":         ("노말", "변화", 0, 85, 0, 40, False, 0, None, None, {"B": -2}, "foe", 0, 0, 0),
    "그림자분신":        ("노말", "변화", 0, None, 0, 15, False, 0, None, None, {"회": 1}, "self", 0, 0, 0),
    "HP회복":         ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "단단해지기":        ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {"B": 1}, "self", 0, 0, 0),
    "작아지기":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {"회": 2}, "self", 0, 0, 0),
    "연막":           ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "웅크리기":         ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {"B": 1}, "self", 0, 0, 0),
    "기충전":          ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "self", 0, 0, 0),
    "참기":           ("노말", "물리", 0, None, 1, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "손가락흔들기":       ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "자폭":           ("노말", "물리", 200, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "알폭탄":          ("노말", "물리", 100, 75, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스피드스타":        ("노말", "특수", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "로케트박치기":       ("노말", "물리", 130, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "가시대포":         ("노말", "물리", 20, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "휘감기":          ("노말", "물리", 10, 100, 0, 35, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "알낳기":          ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "뱀눈초리":         ("노말", "변화", 0, 100, 0, 30, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "구슬던지기":        ("노말", "물리", 15, 85, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "악마의키스":        ("노말", "변화", 0, 75, 0, 10, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "변신":           ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "잼잼펀치":         ("노말", "물리", 70, 100, 0, 10, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "플래시":          ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "튀어오르기":        ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "self", 0, 0, 0),
    "대폭발":          ("노말", "물리", 250, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마구할퀴기":        ("노말", "물리", 18, 80, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "필살앞니":         ("노말", "물리", 80, 90, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "각지기":          ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {"A": 1}, "self", 0, 0, 0),
    "텍스처":          ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "self", 0, 0, 0),
    "트라이어택":        ("노말", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "분노의앞니":        ("노말", "물리", 0, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "베어가르기":        ("노말", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "대타출동":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "발버둥":          ("노말", "물리", 50, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스케치":          ("노말", "변화", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마음의눈":         ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "코골기":          ("노말", "특수", 50, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "바둥바둥":         ("노말", "물리", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "텍스처2":         ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "방어":           ("노말", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "겁나는얼굴":        ("노말", "변화", 0, 100, 0, 10, False, 0, None, None, {"S": -2}, "foe", 0, 0, 0),
    "배북":           ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "꿰뚫어보기":        ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "멸망의노래":        ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "록온":           ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "버티기":          ("노말", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "칼등치기":         ("노말", "물리", 40, 100, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "뽐내기":          ("노말", "변화", 0, 85, 0, 15, False, 0, None, VolatileStatus.CNF, {"A": 2}, "foe", 0, 0, 0),
    "우유마시기":        ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "검은눈빛":         ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "헤롱헤롱":         ("노말", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "잠꼬대":          ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "치료방울":         ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "은혜갚기":         ("노말", "물리", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "프레젠트":         ("노말", "물리", 0, 90, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "화풀이":          ("노말", "물리", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "신비의부적":        ("노말", "변화", 0, None, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아픔나누기":        ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바톤터치":         ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "self", 0, 0, 0),
    "앵콜":           ("노말", "변화", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "고속스핀":         ("노말", "물리", 50, 100, 0, 40, False, 0, None, None, {"S": 1}, "foe", 0, 0, 0),
    "달콤한향기":        ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {"회": -2}, "foe", 0, 0, 0),
    "아침햇살":         ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "잠재파워":         ("노말", "특수", 60, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "자기암시":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "신속":           ("노말", "물리", 80, 100, 2, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "속이다":          ("노말", "물리", 40, 100, 3, 10, False, 0, None, VolatileStatus.FLI, {}, "foe", 100, 0, 0),
    "소란피기":         ("노말", "특수", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "비축하기":         ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"B": 1, "D": 1}, "self", 0, 0, 0),
    "토해내기":         ("노말", "특수", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "꿀꺽":           ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "객기":           ("노말", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "정신차리기":        ("노말", "물리", 70, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "날따름":          ("노말", "변화", 0, None, 2, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "자연의힘":         ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "도우미":          ("노말", "변화", 0, None, 5, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "희망사항":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "조수":           ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "리사이클":         ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "하품":           ("노말", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "죽기살기":         ("노말", "물리", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "리프레쉬":         ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "비밀의힘":         ("노말", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "보호색":          ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "흔들흔들댄스":       ("노말", "변화", 0, 100, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "태만함":          ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "하이퍼보이스":       ("노말", "특수", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "브레이크크루":       ("노말", "물리", 75, 95, 0, 10, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "웨더볼":          ("노말", "특수", 50, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "냄새구별":         ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "간지르기":         ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {"A": -1, "B": -1}, "foe", 0, 0, 0),
    "블록":           ("노말", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "멀리짖음":         ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {"A": 1}, "self", 0, 0, 0),
    "탐내다":          ("노말", "물리", 60, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "자연의은혜":        ("노말", "물리", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "페인트":          ("노말", "물리", 30, 100, 2, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "경혈찌르기":        ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "self", 0, 0, 0),
    "마지막수단":        ("노말", "특수", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "쥐어짜기":         ("노말", "특수", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "주술":           ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "선취":           ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "흉내쟁이":         ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "뒀다쓰기":         ("노말", "물리", 140, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기가임팩트":        ("노말", "물리", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "락클라임":         ("노말", "물리", 90, 85, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "유혹":           ("노말", "변화", 0, 100, 0, 20, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "심판의뭉치":        ("노말", "특수", 100, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "더블어택":         ("노말", "물리", 35, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "묵사발":          ("노말", "물리", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "심플빔":          ("노말", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "동료만들기":        ("노말", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "당신먼저":         ("노말", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "돌림노래":         ("노말", "특수", 60, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "에코보이스":        ("노말", "특수", 40, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "야금야금":         ("노말", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "껍질깨기":         ("노말", "변화", 0, None, 0, 15, False, 0, None, None, {"B": -1, "D": -1, "A": 2, "C": 2, "S": 2}, "self", 0, 0, 0),
    "미러타입":         ("노말", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "원수갚기":         ("노말", "물리", 70, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기프트패스":        ("노말", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "분발":           ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {"A": 1, "C": 1}, "self", 0, 0, 0),
    "스위프뺨치기":       ("노말", "물리", 25, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아프로브레이크":      ("노말", "물리", 120, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 1/4, 0),
    "테크노버스터":       ("노말", "특수", 120, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "옛노래":          ("노말", "특수", 75, 100, 0, 10, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "부르짖기":         ("노말", "변화", 0, 100, 0, 30, False, 0, None, None, {"A": -1, "C": -1}, "foe", 0, 0, 0),
    "폭음파":          ("노말", "특수", 140, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "친해지기":         ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "비밀이야기":        ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "해피타임":         ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "축하":           ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "self", 0, 0, 0),
    "손에손잡기":        ("노말", "변화", 0, None, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "적당히손봐주기":      ("노말", "물리", 40, 100, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "울트라대시어택":      ("노말", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스포트라이트":       ("노말", "변화", 0, None, 3, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "예민해지기":        ("노말", "변화", 0, None, 0, 30, False, 0, None, None, {}, "self", 0, 0, 0),
    "잠재댄스":         ("노말", "특수", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "진심의공격":        ("노말", "물리", 210, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "나인이볼부스트":      ("노말", "변화", 0, None, 0, 1, False, 0, None, None, {"A": 2, "B": 2, "C": 2, "D": 2, "S": 2}, "self", 0, 0, 0),
    "눈물그렁그렁":       ("노말", "변화", 0, None, 0, 20, False, 0, None, None, {"A": -1, "C": -1}, "foe", 0, 0, 0),
    "멀티어택":         ("노말", "물리", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "브이브이브레이크":     ("노말", "물리", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 불꽃 ─────────────────────────────────────────────
    "불꽃펀치":         ("불꽃", "물리", 75, 100, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "불꽃세례":         ("불꽃", "특수", 40, 100, 0, 25, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "화염방사":         ("불꽃", "특수", 90, 100, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "회오리불꽃":        ("불꽃", "특수", 35, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "불대문자":         ("불꽃", "특수", 110, 85, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "화염자동차":        ("불꽃", "물리", 60, 100, 0, 25, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "성스러운불꽃":       ("불꽃", "물리", 100, 95, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "쾌청":           ("불꽃", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "열풍":           ("불꽃", "특수", 95, 90, 0, 10, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "도깨비불":         ("불꽃", "변화", 0, 85, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "분화":           ("불꽃", "특수", 150, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "브레이즈킥":        ("불꽃", "물리", 85, 90, 0, 10, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "블러스트번":        ("불꽃", "특수", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "오버히트":         ("불꽃", "특수", 130, 90, 0, 5, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "플레어드라이브":      ("불꽃", "물리", 120, 100, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 1/3, 0),
    "불꽃엄니":         ("불꽃", "물리", 65, 95, 0, 15, False, 0, StatusCondition.BRN, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "분연":           ("불꽃", "특수", 80, 100, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "마그마스톰":        ("불꽃", "특수", 100, 75, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "불꽃튀기기":        ("불꽃", "특수", 70, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "니트로차지":        ("불꽃", "물리", 50, 100, 0, 20, False, 0, None, None, {"S": 1}, "foe", 0, 0, 0),
    "불태우기":         ("불꽃", "특수", 60, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "연옥":           ("불꽃", "특수", 100, 50, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "불꽃의맹세":        ("불꽃", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "히트스탬프":        ("불꽃", "물리", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "화염탄":          ("불꽃", "특수", 100, 100, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "푸른불꽃":         ("불꽃", "특수", 130, 85, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "불꽃춤":          ("불꽃", "특수", 80, 100, 0, 10, False, 0, None, None, {"C": 1}, "foe", 0, 0, 0),
    "V제너레이트":       ("불꽃", "물리", 180, 95, 0, 5, False, 0, None, None, {"B": -1, "D": -1, "S": -1}, "foe", 0, 0, 0),
    "크로스플레임":       ("불꽃", "특수", 100, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "매지컬플레임":       ("불꽃", "특수", 75, 100, 0, 10, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "다이내믹풀플레임":     ("불꽃", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "불꽃채찍":         ("불꽃", "물리", 80, 100, 0, 15, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "불사르기":         ("불꽃", "특수", 130, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트랩셸":          ("불꽃", "특수", 150, 100, -3, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "깜짝헤드":         ("불꽃", "특수", 150, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "이글이글번":        ("불꽃", "물리", 60, 100, 0, 20, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    # ── 물 ─────────────────────────────────────────────
    "물대포":          ("물", "특수", 40, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하이드로펌프":       ("물", "특수", 110, 80, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파도타기":         ("물", "특수", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "거품광선":         ("물", "특수", 65, 100, 0, 20, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "껍질에숨기":        ("물", "변화", 0, None, 0, 40, False, 0, None, None, {"B": 1}, "self", 0, 0, 0),
    "폭포오르기":        ("물", "물리", 80, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 20, 0, 0),
    "껍질끼우기":        ("물", "물리", 35, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "거품":           ("물", "특수", 40, 100, 0, 30, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "찝게햄머":         ("물", "물리", 100, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "대포무노포":        ("물", "특수", 65, 85, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "비바라기":         ("물", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바다회오리":        ("물", "특수", 35, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "다이빙":          ("물", "물리", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하이드로캐논":       ("물", "특수", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "해수스파우팅":       ("물", "특수", 150, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "탁류":           ("물", "특수", 90, 85, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "물놀이":          ("물", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "물의파동":         ("물", "특수", 60, 100, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "소금물":          ("물", "특수", 65, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아쿠아링":         ("물", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "아쿠아테일":        ("물", "물리", 90, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아쿠아제트":        ("물", "물리", 40, 100, 1, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "물붓기":          ("물", "변화", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "열탕":           ("물", "특수", 80, 100, 0, 15, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "물의맹세":         ("물", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "셸블레이드":        ("물", "물리", 75, 95, 0, 10, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "스팀버스트":        ("물", "특수", 110, 95, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "물수리검":         ("물", "특수", 15, 100, 1, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "근원의파동":        ("물", "특수", 110, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "슈퍼아쿠아토네이도":    ("물", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "물거품아리아":       ("물", "특수", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바다의심포니":       ("물", "특수", 195, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아쿠아브레이크":      ("물", "물리", 85, 100, 0, 10, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "참방참방서핑":       ("물", "특수", 90, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "생생버블":         ("물", "특수", 60, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 1.0),
    # ── 풀 ─────────────────────────────────────────────
    "덩굴채찍":         ("풀", "물리", 45, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "흡수":           ("풀", "특수", 20, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "메가드레인":        ("풀", "특수", 40, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "씨뿌리기":         ("풀", "변화", 0, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "잎날가르기":        ("풀", "물리", 55, 95, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "솔라빔":          ("풀", "특수", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "저리가루":         ("풀", "변화", 0, 75, 0, 30, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "수면가루":         ("풀", "변화", 0, 75, 0, 15, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "꽃잎댄스":         ("풀", "특수", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "버섯포자":         ("풀", "변화", 0, 100, 0, 15, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "목화포자":         ("풀", "변화", 0, 100, 0, 40, False, 0, None, None, {"S": -2}, "foe", 0, 0, 0),
    "기가드레인":        ("풀", "특수", 75, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "광합성":          ("풀", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "뿌리박기":         ("풀", "변화", 0, None, 0, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "바늘팔":          ("풀", "물리", 60, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "아로마테라피":       ("풀", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "풀피리":          ("풀", "변화", 0, 55, 0, 15, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "기관총":          ("풀", "물리", 25, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하드플랜트":        ("풀", "특수", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "메지컬리프":        ("풀", "특수", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "리프블레이드":       ("풀", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "고민씨":          ("풀", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "씨폭탄":          ("풀", "물리", 80, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "에너지볼":         ("풀", "특수", 90, 100, 0, 10, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "리프스톰":         ("풀", "특수", 130, 90, 0, 5, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "파워휩":          ("풀", "물리", 120, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "풀묶기":          ("풀", "특수", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "우드해머":         ("풀", "물리", 120, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 1/3, 0),
    "시드플레어":        ("풀", "특수", 120, 85, 0, 5, False, 0, None, None, {"D": -2}, "foe", 0, 0, 0),
    "풀의맹세":         ("풀", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "우드호른":         ("풀", "물리", 75, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "그래스믹서":        ("풀", "특수", 65, 90, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "코튼가드":         ("풀", "변화", 0, None, 0, 10, False, 0, None, None, {"B": 3}, "self", 0, 0, 0),
    "숲의저주":         ("풀", "변화", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "꽃보라":          ("풀", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "그래스필드":        ("풀", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "니들가드":         ("풀", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "블룸샤인엑스트라":     ("풀", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "힘흡수":          ("풀", "변화", 0, 100, 0, 10, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "솔라블레이드":       ("풀", "물리", 125, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "나뭇잎":          ("풀", "물리", 40, 100, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트로피컬킥":        ("풀", "물리", 70, 100, 0, 15, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "쑥쑥봄버":         ("풀", "물리", 100, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 전기 ─────────────────────────────────────────────
    "번개펀치":         ("전기", "물리", 75, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "전기쇼크":         ("전기", "특수", 40, 100, 0, 30, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "10만볼트":        ("전기", "특수", 90, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "전기자석파":        ("전기", "변화", 0, 90, 0, 20, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "번개":           ("전기", "특수", 110, 70, 0, 10, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "전자포":          ("전기", "특수", 120, 50, 0, 5, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "스파크":          ("전기", "물리", 65, 100, 0, 20, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "충전":           ("전기", "변화", 0, None, 0, 20, False, 0, None, None, {"D": 1}, "self", 0, 0, 0),
    "볼트태클":         ("전기", "물리", 120, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 1/3, 0),
    "전격파":          ("전기", "특수", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "전자부유":         ("전기", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "번개엄니":         ("전기", "물리", 65, 95, 0, 15, False, 0, StatusCondition.PAR, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "방전":           ("전기", "특수", 80, 100, 0, 15, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "차지빔":          ("전기", "특수", 50, 90, 0, 10, False, 0, None, None, {"C": 1}, "foe", 0, 0, 0),
    "일렉트릭볼":        ("전기", "특수", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "볼트체인지":        ("전기", "특수", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "일렉트릭네트":       ("전기", "특수", 55, 95, 0, 15, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "와일드볼트":        ("전기", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 1/4, 0),
    "뇌격":           ("전기", "물리", 130, 85, 0, 5, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "크로스썬더":        ("전기", "물리", 100, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플라스마샤워":       ("전기", "변화", 0, None, 1, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파라볼라차지":       ("전기", "특수", 65, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "송전":           ("전기", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "괴전파":          ("전기", "변화", 0, 100, 0, 15, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "자기장조작":        ("전기", "변화", 0, None, 0, 20, False, 0, None, None, {"B": 1, "D": 1}, "self", 0, 0, 0),
    "일렉트릭필드":       ("전기", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "볼부비부비":        ("전기", "물리", 20, 100, 0, 20, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "스파킹기가볼트":      ("전기", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "필살피카슛":        ("전기", "물리", 210, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "라이트닝서프라이드":    ("전기", "특수", 175, None, 0, 1, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "찌리리따끔따끔":      ("전기", "물리", 80, 100, 0, 10, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "1000만볼트":      ("전기", "특수", 195, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플라스마피스트":      ("전기", "물리", 100, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파찌파찌액셀":       ("전기", "물리", 80, 100, 2, 10, False, 0, None, None, {"회": 1}, "foe", 0, 0, 0),
    "피카피카썬더":       ("전기", "특수", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "찌릿찌릿일렉":       ("전기", "특수", 60, 100, 0, 20, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    # ── 얼음 ─────────────────────────────────────────────
    "냉동펀치":         ("얼음", "물리", 75, 100, 0, 15, False, 0, StatusCondition.FRZ, None, {}, "foe", 0, 0, 0),
    "흰안개":          ("얼음", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "냉동빔":          ("얼음", "특수", 90, 100, 0, 10, False, 0, StatusCondition.FRZ, None, {}, "foe", 0, 0, 0),
    "눈보라":          ("얼음", "특수", 110, 70, 0, 5, False, 0, StatusCondition.FRZ, None, {}, "foe", 0, 0, 0),
    "오로라빔":         ("얼음", "특수", 65, 100, 0, 20, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "흑안개":          ("얼음", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "눈싸라기":         ("얼음", "특수", 40, 100, 0, 25, False, 0, StatusCondition.FRZ, None, {}, "foe", 0, 0, 0),
    "얼다바람":         ("얼음", "특수", 55, 95, 0, 15, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "싸라기눈":         ("얼음", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아이스볼":         ("얼음", "물리", 30, 90, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "절대영도":         ("얼음", "특수", 0, 30, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "고드름침":         ("얼음", "물리", 25, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "눈사태":          ("얼음", "물리", 60, 100, -4, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "얼음뭉치":         ("얼음", "물리", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "얼음엄니":         ("얼음", "물리", 65, 95, 0, 15, False, 0, StatusCondition.FRZ, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "얼음숨결":         ("얼음", "특수", 60, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "얼다세계":         ("얼음", "특수", 65, 95, 0, 10, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "프리즈볼트":        ("얼음", "물리", 140, 90, 0, 5, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "콜드플레어":        ("얼음", "특수", 140, 90, 0, 5, False, 0, StatusCondition.BRN, None, {}, "foe", 0, 0, 0),
    "고드름떨구기":       ("얼음", "물리", 85, 90, 0, 10, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "프리즈드라이":       ("얼음", "특수", 70, 100, 0, 20, False, 0, StatusCondition.FRZ, None, {}, "foe", 0, 0, 0),
    "레이징지오프리즈":     ("얼음", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아이스해머":        ("얼음", "물리", 100, 90, 0, 10, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "오로라베일":        ("얼음", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "꽁꽁프로스트":       ("얼음", "특수", 100, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 격투 ─────────────────────────────────────────────
    "태권당수":         ("격투", "물리", 50, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "두번치기":         ("격투", "물리", 30, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "점프킥":          ("격투", "물리", 100, 95, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "돌려차기":         ("격투", "물리", 60, 85, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "지옥의바퀴":        ("격투", "물리", 80, 80, 0, 20, False, 0, None, None, {}, "foe", 0, 1/4, 0),
    "안다리걸기":        ("격투", "물리", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "카운터":          ("격투", "물리", 0, 100, -5, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "지구던지기":        ("격투", "물리", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "무릎차기":         ("격투", "물리", 130, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트리플킥":         ("격투", "물리", 10, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기사회생":         ("격투", "물리", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마하펀치":         ("격투", "물리", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "판별":           ("격투", "변화", 0, None, 4, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "폭발펀치":         ("격투", "물리", 100, 50, 0, 5, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "받아던지기":        ("격투", "물리", 70, None, -1, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "크로스촙":         ("격투", "물리", 100, 80, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바위깨기":         ("격투", "물리", 40, 100, 0, 15, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "힘껏펀치":         ("격투", "물리", 150, 100, -3, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "엄청난힘":         ("격투", "물리", 120, 100, 0, 5, False, 0, None, None, {"A": -1, "B": -1}, "foe", 0, 0, 0),
    "리벤지":          ("격투", "물리", 60, 100, -4, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "깨트리다":         ("격투", "물리", 75, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "손바닥치기":        ("격투", "물리", 15, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스카이업퍼":        ("격투", "물리", 85, 90, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "벌크업":          ("격투", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 1, "B": 1}, "self", 0, 0, 0),
    "잠깨움뺨치기":       ("격투", "물리", 70, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "암해머":          ("격투", "물리", 100, 90, 0, 10, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "인파이트":         ("격투", "물리", 120, 100, 0, 5, False, 0, None, None, {"B": -1, "D": -1}, "foe", 0, 0, 0),
    "발경":           ("격투", "물리", 60, 100, 0, 10, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "파동탄":          ("격투", "특수", 80, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "드레인펀치":        ("격투", "물리", 75, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "진공파":          ("격투", "특수", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기합구슬":         ("격투", "특수", 120, 70, 0, 5, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "업어후리기":        ("격투", "물리", 60, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "로킥":           ("격투", "물리", 65, 100, 0, 20, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "퍼스트가드":        ("격투", "변화", 0, None, 3, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "배대뒤치기":        ("격투", "물리", 60, 90, -6, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "목숨걸기":         ("격투", "특수", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "성스러운칼":        ("격투", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "신비의칼":         ("격투", "특수", 85, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플라잉프레스":       ("격투", "물리", 100, 95, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마룻바닥세워막기":     ("격투", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "그로우펀치":        ("격투", "물리", 40, 100, 0, 20, False, 0, None, None, {"A": 1}, "foe", 0, 0, 0),
    "전력무쌍격렬권":      ("격투", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 독 ─────────────────────────────────────────────
    "독침":           ("독", "물리", 15, 100, 0, 35, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "용해액":          ("독", "특수", 40, 100, 0, 30, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "독가루":          ("독", "변화", 0, 75, 0, 35, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "맹독":           ("독", "변화", 0, 90, 0, 10, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "스모그":          ("독", "특수", 30, 70, 0, 20, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "오물공격":         ("독", "특수", 65, 100, 0, 20, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "독가스":          ("독", "변화", 0, 90, 0, 40, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "녹기":           ("독", "변화", 0, None, 0, 20, False, 0, None, None, {"B": 2}, "self", 0, 0, 0),
    "오물폭탄":         ("독", "특수", 90, 100, 0, 10, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "독엄니":          ("독", "물리", 50, 100, 0, 15, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "포이즌테일":        ("독", "물리", 50, 100, 0, 25, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "위액":           ("독", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "독압정":          ("독", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "독찌르기":         ("독", "물리", 80, 100, 0, 20, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "크로스포이즌":       ("독", "물리", 70, 100, 0, 20, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "더스트슈트":        ("독", "물리", 120, 80, 0, 5, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "베놈쇼크":         ("독", "특수", 65, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "오물웨이브":        ("독", "특수", 95, 100, 0, 10, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "똬리틀기":         ("독", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 1, "B": 1, "명": 1}, "self", 0, 0, 0),
    "애시드봄":         ("독", "특수", 40, 100, 0, 20, False, 0, None, None, {"D": -2}, "foe", 0, 0, 0),
    "클리어스모그":       ("독", "특수", 50, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트림":           ("독", "특수", 120, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "베놈트랩":         ("독", "변화", 0, 100, 0, 20, False, 0, None, None, {"A": -1, "C": -1, "S": -1}, "foe", 0, 0, 0),
    "애시드포이즌딜리트":    ("독", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "토치카":          ("독", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "독실":           ("독", "변화", 0, 100, 0, 20, False, 0, StatusCondition.PSN, None, {"S": -1}, "foe", 0, 0, 0),
    "정화":           ("독", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 땅 ─────────────────────────────────────────────
    "모래뿌리기":        ("땅", "변화", 0, 100, 0, 15, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "지진":           ("땅", "물리", 100, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "땅가르기":         ("땅", "물리", 0, 30, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "구멍파기":         ("땅", "물리", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "뼈다귀치기":        ("땅", "물리", 65, 85, 0, 20, False, 0, None, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "뼈다귀부메랑":       ("땅", "물리", 50, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "진흙뿌리기":        ("땅", "특수", 20, 100, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "압정뿌리기":        ("땅", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "본러쉬":          ("땅", "물리", 25, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "매그니튜드":        ("땅", "물리", 0, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "흙놀이":          ("땅", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "모래지옥":         ("땅", "물리", 35, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "머드숏":          ("땅", "특수", 55, 95, 0, 15, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "대지의힘":         ("땅", "특수", 90, 100, 0, 10, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "진흙폭탄":         ("땅", "특수", 65, 85, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "땅고르기":         ("땅", "물리", 60, 100, 0, 20, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "드릴라이너":        ("땅", "물리", 80, 95, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "일구기":          ("땅", "변화", 0, None, 0, 10, False, 0, None, None, {"A": 1, "C": 1}, "foe", 0, 0, 0),
    "사우전드애로":       ("땅", "물리", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사우전드웨이브":      ("땅", "물리", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "그라운드포스":       ("땅", "물리", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "단애의칼":         ("땅", "물리", 120, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "라이징랜드오버":      ("땅", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "모래모으기":        ("땅", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "10만마력":        ("땅", "물리", 95, 95, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "분함의발구르기":      ("땅", "물리", 75, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 비행 ─────────────────────────────────────────────
    "바람일으키기":       ("비행", "특수", 40, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "날개치기":         ("비행", "물리", 60, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "공중날기":         ("비행", "물리", 90, 95, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "쪼기":           ("비행", "물리", 35, 100, 0, 35, False, 0, None, None, {}, "foe", 0, 0, 0),
    "회전부리":         ("비행", "물리", 80, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "따라하기":         ("비행", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "불새":           ("비행", "물리", 140, 90, 0, 5, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "에어로블라스트":      ("비행", "특수", 100, 95, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "깃털댄스":         ("비행", "변화", 0, 100, 0, 15, False, 0, None, None, {"A": -2}, "foe", 0, 0, 0),
    "에어컷터":         ("비행", "특수", 60, 95, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "제비반환":         ("비행", "물리", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "뛰어오르다":        ("비행", "물리", 85, 85, 0, 5, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "날개쉬기":         ("비행", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "쪼아대기":         ("비행", "물리", 60, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "순풍":           ("비행", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "에어슬래시":        ("비행", "특수", 75, 95, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "브레이브버드":       ("비행", "물리", 120, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 1/3, 0),
    "안개제거":         ("비행", "변화", 0, None, 0, 15, False, 0, None, None, {"회": -1}, "foe", 0, 0, 0),
    "수다":           ("비행", "특수", 65, 100, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "프리폴":          ("비행", "물리", 60, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "애크러뱃":         ("비행", "물리", 55, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "폭풍":           ("비행", "특수", 110, 70, 0, 10, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "데스윙":          ("비행", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.75),
    "화룡점정":         ("비행", "물리", 120, 100, 0, 5, False, 0, None, None, {"B": -1, "D": -1}, "foe", 0, 0, 0),
    "파이널다이브클래시":    ("비행", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "부리캐논":         ("비행", "물리", 100, 100, -3, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "둥실둥실폴":        ("비행", "물리", 90, 95, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    # ── 에스퍼 ─────────────────────────────────────────────
    "환상빔":          ("에스퍼", "특수", 65, 100, 0, 20, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "염동력":          ("에스퍼", "특수", 50, 100, 0, 25, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "사이코키네시스":      ("에스퍼", "특수", 90, 100, 0, 10, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "최면술":          ("에스퍼", "변화", 0, 60, 0, 20, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "요가포즈":         ("에스퍼", "변화", 0, None, 0, 40, False, 0, None, None, {"A": 1}, "self", 0, 0, 0),
    "고속이동":         ("에스퍼", "변화", 0, None, 0, 30, False, 0, None, None, {"S": 2}, "self", 0, 0, 0),
    "순간이동":         ("에스퍼", "변화", 0, None, -6, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "배리어":          ("에스퍼", "변화", 0, None, 0, 20, False, 0, None, None, {"B": 2}, "self", 0, 0, 0),
    "빛의장막":         ("에스퍼", "변화", 0, None, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "리플렉터":         ("에스퍼", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "망각술":          ("에스퍼", "변화", 0, None, 0, 20, False, 0, None, None, {"D": 2}, "self", 0, 0, 0),
    "숟가락휘기":        ("에스퍼", "변화", 0, 80, 0, 15, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "꿈먹기":          ("에스퍼", "특수", 100, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "사이코웨이브":       ("에스퍼", "특수", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "잠자기":          ("에스퍼", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "미러코트":         ("에스퍼", "특수", 0, 100, -5, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "미래예지":         ("에스퍼", "특수", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트릭":           ("에스퍼", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "역할":           ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "매직코트":         ("에스퍼", "변화", 0, None, 4, 15, False, 0, None, None, {}, "self", 0, 0, 0),
    "스킬스웹":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "봉인":           ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "라스트버지":        ("에스퍼", "특수", 95, 100, 0, 5, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "미스트볼":         ("에스퍼", "특수", 95, 100, 0, 5, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "코스믹파워":        ("에스퍼", "변화", 0, None, 0, 20, False, 0, None, None, {"B": 1, "D": 1}, "self", 0, 0, 0),
    "신통력":          ("에스퍼", "특수", 80, 100, 0, 20, False, 0, None, VolatileStatus.FLI, {}, "foe", 10, 0, 0),
    "명상":           ("에스퍼", "변화", 0, None, 0, 20, False, 0, None, None, {"C": 1, "D": 1}, "self", 0, 0, 0),
    "사이코부스트":       ("에스퍼", "특수", 140, 90, 0, 5, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "중력":           ("에스퍼", "변화", 0, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "미라클아이":        ("에스퍼", "변화", 0, None, 0, 40, False, 0, None, None, {}, "foe", 0, 0, 0),
    "치유소원":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "사이코시프트":       ("에스퍼", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "회복봉인":         ("에스퍼", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파워트릭":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "파워스웹":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "가드스웹":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하트스웹":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사이코커터":        ("에스퍼", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사념의박치기":       ("에스퍼", "물리", 80, 90, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 20, 0, 0),
    "트릭룸":          ("에스퍼", "변화", 0, None, -7, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "초승달춤":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "가드셰어":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "파워셰어":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "원더룸":          ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사이코쇼크":        ("에스퍼", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "텔레키네시스":       ("에스퍼", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "매직룸":          ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "싱크로노이즈":       ("에스퍼", "특수", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "어시스트파워":       ("에스퍼", "특수", 20, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사이드체인지":       ("에스퍼", "변화", 0, None, 2, 15, False, 0, None, None, {}, "self", 0, 0, 0),
    "치유파동":         ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하트스탬프":        ("에스퍼", "물리", 60, 100, 0, 25, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "사이코브레이크":      ("에스퍼", "특수", 100, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "다른차원홀":        ("에스퍼", "특수", 80, None, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "맥시멈사이브레이커":    ("에스퍼", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사이코필드":        ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스피드스웹":        ("에스퍼", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "지휘":           ("에스퍼", "변화", 0, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "오리진즈슈퍼노바":     ("에스퍼", "특수", 185, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "사이코팽":         ("에스퍼", "물리", 85, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "프리즘레이저":       ("에스퍼", "특수", 160, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "포톤가이저":        ("에스퍼", "특수", 100, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하늘을태우는멸망의빛":   ("에스퍼", "특수", 200, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "콸콸오라":         ("에스퍼", "특수", 80, 95, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 벌레 ─────────────────────────────────────────────
    "더블니들":         ("벌레", "물리", 25, 100, 0, 20, False, 0, StatusCondition.PSN, None, {}, "foe", 0, 0, 0),
    "바늘미사일":        ("벌레", "물리", 25, 95, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "실뿜기":          ("벌레", "변화", 0, 95, 0, 40, False, 0, None, None, {"S": -2}, "foe", 0, 0, 0),
    "흡혈":           ("벌레", "물리", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.5),
    "거미집":          ("벌레", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "연속자르기":        ("벌레", "물리", 40, 95, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "메가폰":          ("벌레", "물리", 120, 85, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "반딧불":          ("벌레", "변화", 0, None, 0, 20, False, 0, None, None, {"C": 3}, "self", 0, 0, 0),
    "은빛바람":         ("벌레", "특수", 60, 100, 0, 5, False, 0, None, None, {"A": 1, "B": 1, "C": 1, "D": 1, "S": 1}, "foe", 0, 0, 0),
    "시그널빔":         ("벌레", "특수", 75, 100, 0, 15, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "유턴":           ("벌레", "물리", 70, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "시저크로스":        ("벌레", "물리", 80, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "벌레의야단법석":      ("벌레", "특수", 90, 100, 0, 10, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "벌레먹음":         ("벌레", "물리", 60, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "공격지령":         ("벌레", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "방어지령":         ("벌레", "변화", 0, None, 0, 10, False, 0, None, None, {"B": 1, "D": 1}, "self", 0, 0, 0),
    "회복지령":         ("벌레", "변화", 0, None, 0, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "분노가루":         ("벌레", "변화", 0, None, 2, 20, False, 0, None, None, {}, "self", 0, 0, 0),
    "나비춤":          ("벌레", "변화", 0, None, 0, 20, False, 0, None, None, {"C": 1, "D": 1, "S": 1}, "self", 0, 0, 0),
    "벌레의저항":        ("벌레", "특수", 50, 100, 0, 20, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "하드롤러":         ("벌레", "물리", 65, 100, 0, 20, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "끈적끈적네트":       ("벌레", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "마지막일침":        ("벌레", "물리", 50, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "분진":           ("벌레", "변화", 0, 100, 1, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "엉겨붙기":         ("벌레", "특수", 20, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "절대포식회전참":      ("벌레", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "만나자마자":        ("벌레", "물리", 90, 100, 2, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "꽃가루경단":        ("벌레", "특수", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "덤벼들기":         ("벌레", "물리", 80, 100, 0, 15, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    # ── 바위 ─────────────────────────────────────────────
    "돌떨구기":         ("바위", "물리", 50, 90, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스톤샤워":         ("바위", "물리", 75, 90, 0, 10, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "모래바람":         ("바위", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "구르기":          ("바위", "물리", 30, 90, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "원시의힘":         ("바위", "특수", 60, 100, 0, 5, False, 0, None, None, {"A": 1, "B": 1, "C": 1, "D": 1, "S": 1}, "foe", 0, 0, 0),
    "암석봉인":         ("바위", "물리", 60, 95, 0, 15, False, 0, None, None, {"S": -1}, "foe", 0, 0, 0),
    "락블레스트":        ("바위", "물리", 25, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "록커트":          ("바위", "변화", 0, None, 0, 20, False, 0, None, None, {"S": 2}, "self", 0, 0, 0),
    "파워젬":          ("바위", "특수", 80, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "암석포":          ("바위", "물리", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스톤에지":         ("바위", "물리", 100, 80, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스텔스록":         ("바위", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "양날박치기":        ("바위", "물리", 150, 80, 0, 5, False, 0, None, None, {}, "foe", 0, 1/2, 0),
    "와이드가드":        ("바위", "변화", 0, None, 3, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "떨어뜨리기":        ("바위", "물리", 50, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "다이아스톰":        ("바위", "물리", 100, 95, 0, 5, False, 0, None, None, {"B": 2}, "foe", 0, 0, 0),
    "월즈엔드폴":        ("바위", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "액셀록":          ("바위", "물리", 40, 100, 1, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "레이디얼에지스톰":     ("바위", "물리", 190, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 고스트 ─────────────────────────────────────────────
    "나이트헤드":        ("고스트", "특수", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "이상한빛":         ("고스트", "변화", 0, 100, 0, 10, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "핥기":           ("고스트", "물리", 30, 100, 0, 30, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "악몽":           ("고스트", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "저주":           ("고스트", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "원한":           ("고스트", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "길동무":          ("고스트", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "섀도볼":          ("고스트", "특수", 80, 100, 0, 15, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "원념":           ("고스트", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "놀래키기":         ("고스트", "물리", 30, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "섀도펀치":         ("고스트", "물리", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "섀도크루":         ("고스트", "물리", 70, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "야습":           ("고스트", "물리", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "괴상한바람":        ("고스트", "특수", 60, 100, 0, 5, False, 0, None, None, {"A": 1, "B": 1, "C": 1, "D": 1, "S": 1}, "foe", 0, 0, 0),
    "섀도다이브":        ("고스트", "물리", 120, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "병상첨병":         ("고스트", "특수", 65, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "고스트다이브":       ("고스트", "물리", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "핼러윈":          ("고스트", "변화", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "무한암야로의유인":     ("고스트", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "그림자꿰매기":       ("고스트", "물리", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "섀도애로우즈스트라이크":  ("고스트", "물리", 180, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "칠성탈혼퇴":        ("고스트", "물리", 195, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "섀도본":          ("고스트", "물리", 85, 100, 0, 10, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "섀도스틸":         ("고스트", "물리", 90, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "섀도레이":         ("고스트", "특수", 100, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "문라이트블래스터":     ("고스트", "특수", 200, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 드래곤 ─────────────────────────────────────────────
    "용의분노":         ("드래곤", "특수", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "역린":           ("드래곤", "물리", 120, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "용의숨결":         ("드래곤", "특수", 60, 100, 0, 20, False, 0, StatusCondition.PAR, None, {}, "foe", 0, 0, 0),
    "회오리":          ("드래곤", "특수", 40, 100, 0, 20, False, 0, None, VolatileStatus.FLI, {}, "foe", 20, 0, 0),
    "드래곤크루":        ("드래곤", "물리", 80, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "용의춤":          ("드래곤", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 1, "S": 1}, "self", 0, 0, 0),
    "용의파동":         ("드래곤", "특수", 85, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "드래곤다이브":       ("드래곤", "물리", 100, 75, 0, 10, False, 0, None, VolatileStatus.FLI, {}, "foe", 20, 0, 0),
    "용성군":          ("드래곤", "특수", 130, 90, 0, 5, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "시간의포효":        ("드래곤", "특수", 150, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "공간절단":         ("드래곤", "특수", 100, 95, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "드래곤테일":        ("드래곤", "물리", 60, 90, -6, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "더블촙":          ("드래곤", "물리", 40, 90, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "얼티메이트드래곤번":    ("드래곤", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "코어퍼니셔":        ("드래곤", "특수", 100, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스케일노이즈":       ("드래곤", "특수", 110, 100, 0, 5, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "드래곤해머":        ("드래곤", "물리", 90, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "브레이징소울비트":     ("드래곤", "특수", 185, None, 0, 1, False, 0, None, None, {"A": 1, "B": 1, "C": 1, "D": 1, "S": 1}, "foe", 0, 0, 0),
    # ── 악 ─────────────────────────────────────────────
    "물기":           ("악", "물리", 60, 100, 0, 25, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "도둑질":          ("악", "물리", 60, 100, 0, 25, False, 0, None, None, {}, "foe", 0, 0, 0),
    "속여때리기":        ("악", "물리", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "따라가때리기":       ("악", "물리", 40, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "깨물어부수기":       ("악", "물리", 80, 100, 0, 15, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "집단구타":         ("악", "물리", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "트집":           ("악", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "부추기기":         ("악", "변화", 0, 100, 0, 15, False, 0, None, VolatileStatus.CNF, {"C": 1}, "foe", 0, 0, 0),
    "추억의선물":        ("악", "변화", 0, 100, 0, 10, False, 0, None, None, {"A": -2, "C": -2}, "foe", 0, 0, 0),
    "도발":           ("악", "변화", 0, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "탁쳐서떨구기":       ("악", "물리", 65, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "가로챔":          ("악", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "거짓울음":         ("악", "변화", 0, 100, 0, 20, False, 0, None, None, {"D": -2}, "foe", 0, 0, 0),
    "보복":           ("악", "물리", 50, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "승부굳히기":        ("악", "물리", 60, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "금제":           ("악", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "내던지기":         ("악", "물리", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "혼내기":          ("악", "물리", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기습":           ("악", "물리", 70, 100, 1, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "악의파동":         ("악", "특수", 80, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 20, 0, 0),
    "깜짝베기":         ("악", "물리", 70, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바꿔치기":         ("악", "변화", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "나쁜음모":         ("악", "변화", 0, None, 0, 20, False, 0, None, None, {"C": 2}, "self", 0, 0, 0),
    "다크홀":          ("악", "변화", 0, 50, 0, 10, False, 0, StatusCondition.SLP, None, {}, "foe", 0, 0, 0),
    "손톱갈기":         ("악", "변화", 0, None, 0, 15, False, 0, None, None, {"A": 1, "명": 1}, "self", 0, 0, 0),
    "속임수":          ("악", "물리", 95, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "순서미루기":        ("악", "변화", 0, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "나이트버스트":       ("악", "특수", 85, 95, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "바크아웃":         ("악", "특수", 55, 95, 0, 15, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "막말내뱉기":        ("악", "변화", 0, 100, 0, 20, False, 0, None, None, {"A": -1, "C": -1}, "foe", 0, 0, 0),
    "뒤집어엎기":        ("악", "변화", 0, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "다른차원러시":       ("악", "물리", 100, None, 0, 5, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "블랙홀이클립스":      ("악", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "DD래리어트":       ("악", "물리", 85, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "지옥찌르기":        ("악", "물리", 80, 100, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기어오르기":        ("악", "물리", 20, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "세차게휘두르기":      ("악", "물리", 60, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "하이퍼다크크러셔":     ("악", "물리", 180, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아그아그존":        ("악", "특수", 80, 95, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    # ── 강철 ─────────────────────────────────────────────
    "강철날개":         ("강철", "물리", 70, 90, 0, 25, False, 0, None, None, {"B": 1}, "foe", 0, 0, 0),
    "아이언테일":        ("강철", "물리", 100, 75, 0, 15, False, 0, None, None, {"B": -1}, "foe", 0, 0, 0),
    "메탈크로우":        ("강철", "물리", 50, 95, 0, 35, False, 0, None, None, {"A": 1}, "foe", 0, 0, 0),
    "코멧펀치":         ("강철", "물리", 90, 90, 0, 10, False, 0, None, None, {"A": 1}, "foe", 0, 0, 0),
    "금속음":          ("강철", "변화", 0, 85, 0, 40, False, 0, None, None, {"D": -2}, "foe", 0, 0, 0),
    "철벽":           ("강철", "변화", 0, None, 0, 15, False, 0, None, None, {"B": 2}, "self", 0, 0, 0),
    "파멸의소원":        ("강철", "특수", 140, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "자이로볼":         ("강철", "물리", 0, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "메탈버스트":        ("강철", "물리", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "불릿펀치":         ("강철", "물리", 40, 100, 1, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "미러숏":          ("강철", "특수", 65, 85, 0, 10, False, 0, None, None, {"명": -1}, "foe", 0, 0, 0),
    "러스터캐논":        ("강철", "특수", 80, 100, 0, 10, False, 0, None, None, {"D": -1}, "foe", 0, 0, 0),
    "아이언헤드":        ("강철", "물리", 80, 100, 0, 15, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    "마그넷봄":         ("강철", "물리", 60, None, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "바디퍼지":         ("강철", "변화", 0, None, 0, 15, False, 0, None, None, {"S": 2}, "self", 0, 0, 0),
    "헤비봄버":         ("강철", "물리", 0, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "기어체인지":        ("강철", "변화", 0, None, 0, 10, False, 0, None, None, {"A": 1, "S": 2}, "self", 0, 0, 0),
    "기어소서":         ("강철", "물리", 50, 85, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "킹실드":          ("강철", "변화", 0, None, 4, 10, False, 0, None, None, {}, "self", 0, 0, 0),
    "초월나선연격":       ("강철", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "어시스트기어":       ("강철", "변화", 0, None, 0, 20, False, 0, None, None, {"A": 1, "C": 1}, "self", 0, 0, 0),
    "앵커숏":          ("강철", "물리", 80, 100, 0, 20, False, 0, None, None, {}, "foe", 0, 0, 0),
    "스마트호른":        ("강철", "물리", 70, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "메테오드라이브":      ("강철", "물리", 100, 100, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
    "선샤인스매셔":       ("강철", "물리", 200, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "더블펀처":         ("강철", "물리", 60, 100, 0, 5, False, 0, None, VolatileStatus.FLI, {}, "foe", 30, 0, 0),
    # ── 페어리 ─────────────────────────────────────────────
    "천사의키스":        ("페어리", "변화", 0, 75, 0, 10, False, 0, None, VolatileStatus.CNF, {}, "foe", 0, 0, 0),
    "애교부리기":        ("페어리", "변화", 0, 100, 0, 20, False, 0, None, None, {"A": -2}, "foe", 0, 0, 0),
    "달의불빛":         ("페어리", "변화", 0, None, 0, 5, False, 0, None, None, {}, "self", 0, 0, 0),
    "차밍보이스":        ("페어리", "특수", 40, None, 0, 15, False, 0, None, None, {}, "foe", 0, 0, 0),
    "드레인키스":        ("페어리", "특수", 50, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0.75),
    "트릭가드":         ("페어리", "변화", 0, None, 3, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플라워가드":        ("페어리", "변화", 0, None, 0, 10, False, 0, None, None, {"B": 1}, "foe", 0, 0, 0),
    "미스트필드":        ("페어리", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "치근거리기":        ("페어리", "물리", 90, 90, 0, 10, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "요정의바람":        ("페어리", "특수", 40, 100, 0, 30, False, 0, None, None, {}, "foe", 0, 0, 0),
    "문포스":          ("페어리", "특수", 95, 100, 0, 15, False, 0, None, None, {"C": -1}, "foe", 0, 0, 0),
    "페어리록":         ("페어리", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "아로마미스트":       ("페어리", "변화", 0, None, 0, 20, False, 0, None, None, {"D": 1}, "foe", 0, 0, 0),
    "지오컨트롤":        ("페어리", "변화", 0, None, 0, 10, False, 0, None, None, {"C": 2, "D": 2, "S": 2}, "self", 0, 0, 0),
    "매지컬샤인":        ("페어리", "특수", 80, 100, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "초롱초롱눈동자":      ("페어리", "변화", 0, 100, 1, 30, False, 0, None, None, {"A": -1}, "foe", 0, 0, 0),
    "파멸의빛":         ("페어리", "특수", 140, 90, 0, 5, False, 0, None, None, {}, "foe", 0, 1/2, 0),
    "러블리스타임팩트":     ("페어리", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플라워힐":         ("페어리", "변화", 0, None, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "알로라의수호자":      ("페어리", "특수", 0, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "플뢰르캐논":        ("페어리", "특수", 130, 90, 0, 5, False, 0, None, None, {"C": -2}, "foe", 0, 0, 0),
    "자연의분노":        ("페어리", "특수", 0, 90, 0, 10, False, 0, None, None, {}, "foe", 0, 0, 0),
    "투닥투닥프렌드타임":    ("페어리", "물리", 190, None, 0, 1, False, 0, None, None, {}, "foe", 0, 0, 0),
    "반짝반짝스톰":       ("페어리", "특수", 120, 85, 0, 5, False, 0, None, None, {}, "foe", 0, 0, 0),
}

non_contact_physical = {
    # 노말
    "가시대포", "고양이돈받기", "구슬던지기", "대폭발", "비밀의힘", "알폭탄", "자연의은혜", "자폭", "페인트", "프레젠트",
    # 불꽃
    "성스러운불꽃", "화염볼",
    # 물
    "아쿠아커터",
    # 풀
    "G의힘", "꽃보라", "나뭇잎", "덩굴방망이", "드럼어택", "씨기관총", "씨폭탄", "잎날가르기", "트릭플라워",
    # 전기
    "오라휠", "크로스썬더",
    # 얼음
    "고드름떨구기", "고드름침", "얼음뭉치", "프리즈볼트",
    # 격투
    "3연화살", "스타어설트",
    # 독
    "더스트슈트", "독침", "독침천발",
    # 땅
    "그라운드포스", "단애의칼", "땅가르기", "땅고르기", "매그니튜드", "모래지옥", "본러시", "뼈다귀부메랑", "뼈다귀치기", "사우전드애로", "사우전드웨이브", "지진",
    # 비행
    "부리캐논", "불새",
    # 에스퍼
    "사이코커터",
    # 벌레
    "공격지령", "더블니들", "바늘미사일",
    # 바위
    "다이아스톰", "돌떨구기", "떨어뜨리기", "록블라스트", "소금절이", "스톤샤워", "스톤에지", "암석봉인", "암석포",
    # 고스트
    "그림자꿰매기", "섀도본", "성묘", "폴터가이스트",
    # 드래곤
    "드래곤애로", "스케일샷", "한판내기",
    # 악
    "내던지기", "집단구타",
    # 강철
    "거대해머", "마그넷봄", "메탈버스트"
}

contact_special = {
    # 노말
    "마지막수단", "쥐어짜기",
    # 풀
    "꽃잎댄스", "풀묶기",
    # 전기
    "라이트닝드라이브",
    # 벌레
    "엉겨붙기",
    # 페어리
    "드레인키스"
}

# 새로운 규칙을 적용하여 갱신된 _MDB 생성
_MDB = {}
for move_name, original_tuple in _OLD_MDB.items():
    move_type, category = original_tuple[0], original_tuple[1]
    
    # 기본 접촉 판정 조건 설정
    if category == "물리":
        contact_value = True
    else:  # 특수기 및 변화기
        contact_value = False
        
    # 예외 처리 반영
    if move_name in non_contact_physical:
        contact_value = False
    elif move_name in contact_special:
        contact_value = True
        
    # 기존 튜플에서 6번째 인덱스(contact)만 새로 계산된 값으로 변경하여 조립
    new_tuple = (
        original_tuple[0],  # type
        original_tuple[1],  # category
        original_tuple[2],  # power
        original_tuple[3],  # accuracy
        original_tuple[4],  # priority
        original_tuple[5],  # pp
        contact_value,      # contact (★ 새로 판정된 값 적용)
        original_tuple[7],  # effect_chance
        original_tuple[8],  # status
        original_tuple[9],  # volatile
        original_tuple[10], # stat_changes
        original_tuple[11], # target
        original_tuple[12], # flinch_chance
        original_tuple[13], # recoil_ratio
        original_tuple[14]  # drain_ratio
    )
    _MDB[move_name] = new_tuple

# ── 락블래스트 별칭 통합 ─────────────────────────────────
for alias in ("락블레스트", "락블래스트"):
    if alias not in _MDB:
        _MDB[alias] = _MDB.get("락블래스트") or _MDB.get("락블레스트")
_MDB["스톤샤셔"] = _MDB["스톤에지"]  # 동일 데이터


# ── 2턴 기술 집합 ───────────────────────────────────────────
TWO_TURN_MOVES: set[str] = {
    "고스트다이브", "하늘날기", "다이빙", "구멍파기",
    "솔라빔", "솔라블레이드", "하늘높이날기", "로켓박치기",
    "얼음공이", "냉동의숨결",
}
INVULNERABLE_CHARGE_MOVES: set[str] = {
    "고스트다이브", "하늘날기", "다이빙", "구멍파기", "얼음공이", "냉동의숨결",
}

# ── 타입별 반감열매 (공격 타입→열매이름) ─────────────────────
RESIST_BERRY: dict[str, str] = {
    "노말":"자뭉열매","불꽃":"오카열매","물":"린드열매","전기":"야파열매",
    "풀":"슈캐열매","얼음":"수불열매","격투":"하반열매","독":"악키열매",
    "땅":"바코열매","바위":"로셀열매","비행":"버치열매","에스퍼":"야타비열매",
    "벌레":"리체열매","고스트":"애슈열매","드래곤":"타라프열매",
    "악":"으름열매","강철":"치리열매","페어리":"캄라열매",
}

# ── 타입 Z크리스탈 ──────────────────────────────────────────
Z_CRYSTAL_TYPE: dict[str, str] = {
    "노말Z":"노말","격투Z":"격투","비행Z":"비행","독Z":"독","땅Z":"땅",
    "바위Z":"바위","벌레Z":"벌레","고스트Z":"고스트","강철Z":"강철",
    "불꽃Z":"불꽃","물Z":"물","풀Z":"풀","전기Z":"전기","에스퍼Z":"에스퍼",
    "얼음Z":"얼음","드래곤Z":"드래곤","악Z":"악","페어리Z":"페어리",
}



def _make_move(name: str) -> Optional[Move]:
    """기술 이름으로 Move 객체를 생성합니다."""
    row = _MDB.get(name)
    if row is None:
        return None
    (type_ko, cat_ko, power, accuracy, priority, pp, contact,
     eff_chance, status, volatile, stat_changes, target,
     flinch, recoil, drain) = row

    type_  = PokemonType(type_ko)
    cat    = MoveCategory(cat_ko)
    effect = MoveEffect(
        chance       = eff_chance,
        status       = status,
        volatile     = volatile,
        stat_changes = stat_changes,
        target       = target,
        flinch_chance= flinch,
        recoil_ratio = recoil,
        drain_ratio  = drain,
    )
    return Move(
        name     = name,
        type_    = type_,
        category = cat,
        power    = power,
        accuracy = accuracy,
        priority = priority,
        pp       = pp,
        effect   = effect,
        contact  = contact,
    )


# ══════════════════════════════════════════════════════════
#  포켓몬 CSV 로더
# ══════════════════════════════════════════════════════════
THEPOKEMONCSV='''번호,이름_한글,이름_영문,타입1,타입2,H,A,B,C,D,S,총합
1,이상해씨,Bulbasaur,grass,poison,45,49,49,65,65,45,318
2,이상해풀,Ivysaur,grass,poison,60,62,63,80,80,60,405
3,이상해꽃,Venusaur,grass,poison,80,82,83,100,100,80,525
4,파이리,Charmander,fire,,39,52,43,60,50,65,309
5,리자드,Charmeleon,fire,,58,64,58,80,65,80,405
6,리자몽,Charizard,fire,flying,78,84,78,109,85,100,534
7,꼬부기,Squirtle,water,,44,48,65,50,64,43,314
8,어니부기,Wartortle,water,,59,63,80,65,80,58,405
9,거북왕,Blastoise,water,,79,83,100,85,105,78,530
10,캐터피,Caterpie,bug,,45,30,35,20,20,45,195
11,단데기,Metapod,bug,,50,20,55,25,25,30,205
12,버터플,Butterfree,bug,flying,60,45,50,90,80,70,395
13,뿔충이,Weedle,bug,poison,40,35,30,20,20,50,195
14,딱충이,Kakuna,bug,poison,45,25,50,25,25,35,205
15,독침붕,Beedrill,bug,poison,65,90,40,45,80,75,395
16,구구,Pidgey,normal,flying,40,45,40,35,35,56,251
17,피죤,Pidgeotto,normal,flying,63,60,55,50,50,71,349
18,피죤투,Pidgeot,normal,flying,83,80,75,70,70,101,479
19,꼬렛,Rattata,normal,,30,56,35,25,35,72,253
20,레트라,Raticate,normal,,55,81,60,50,70,97,413
21,깨비참,Spearow,normal,flying,40,60,30,31,31,70,262
22,깨비드릴조,Fearow,normal,flying,65,90,65,61,61,100,442
23,아보,Ekans,poison,,35,60,44,40,54,55,288
24,아보크,Arbok,poison,,60,95,69,65,79,80,448
25,피카츄,Pikachu,electric,,35,55,40,50,50,90,320
26,라이츄,Raichu,electric,,60,90,55,90,80,110,485
27,모래두지,Sandshrew,ground,,50,75,85,20,30,40,300
28,고지,Sandslash,ground,,75,100,110,45,55,65,450
29,니드런♀,Nidoran-f,poison,,55,47,52,40,40,41,275
30,니드리나,Nidorina,poison,,70,62,67,55,55,56,365
31,니드퀸,Nidoqueen,poison,ground,90,92,87,75,85,76,505
32,니드런♂,Nidoran-m,poison,,46,57,40,40,40,50,273
33,니드리노,Nidorino,poison,,61,72,57,55,55,65,365
34,니드킹,Nidoking,poison,ground,81,102,77,85,75,85,505
35,삐삐,Clefairy,fairy,,70,45,48,60,65,35,323
36,픽시,Clefable,fairy,,95,70,73,95,90,60,483
37,식스테일,Vulpix,fire,,38,41,40,50,65,65,299
38,나인테일,Ninetales,fire,,73,76,75,81,100,100,505
39,푸린,Jigglypuff,normal,fairy,115,45,20,45,25,20,270
40,푸크린,Wigglytuff,normal,fairy,140,70,45,85,50,45,435
41,주뱃,Zubat,poison,flying,40,45,35,30,40,55,245
42,골뱃,Golbat,poison,flying,75,80,70,65,75,90,455
43,뚜벅쵸,Oddish,grass,poison,45,50,55,75,65,30,320
44,냄새꼬,Gloom,grass,poison,60,65,70,85,75,40,395
45,라플레시아,Vileplume,grass,poison,75,80,85,110,90,50,490
46,파라스,Paras,bug,grass,35,70,55,45,55,25,285
47,파라섹트,Parasect,bug,grass,60,95,80,60,80,30,405
48,콘팡,Venonat,bug,poison,60,55,50,40,55,45,305
49,도나리,Venomoth,bug,poison,70,65,60,90,75,90,450
50,디그다,Diglett,ground,,10,55,25,35,45,95,265
51,닥트리오A,Dugtrio,ground,steel,35,100,60,50,70,110,425
52,나옹,Meowth,normal,,40,45,35,40,40,90,290
53,페르시온,Persian,normal,,65,70,60,65,65,115,440
54,고라파덕,Psyduck,water,,50,52,48,65,50,55,320
55,골덕,Golduck,water,,80,82,78,95,80,85,500
56,망키,Mankey,fighting,,40,80,35,35,45,70,305
57,성원숭,Primeape,fighting,,65,105,60,60,70,95,455
58,가디,Growlithe,fire,,55,70,45,70,50,60,350
59,윈디,Arcanine,fire,,90,110,80,100,80,95,555
60,발챙이,Poliwag,water,,40,50,40,40,40,90,300
61,슈륙챙이,Poliwhirl,water,,65,65,65,50,50,90,385
62,강챙이,Poliwrath,water,fighting,90,95,95,70,90,70,510
63,캐이시,Abra,psychic,,25,20,15,105,55,90,310
64,윤겔라,Kadabra,psychic,,40,35,30,120,70,105,400
65,후딘,Alakazam,psychic,,55,50,45,135,95,120,500
66,알통몬,Machop,fighting,,70,80,50,35,35,35,305
67,근육몬,Machoke,fighting,,80,100,70,50,60,45,405
68,괴력몬,Machamp,fighting,,90,130,80,65,85,55,505
69,모다피,Bellsprout,grass,poison,50,75,35,70,30,40,300
70,우츠동,Weepinbell,grass,poison,65,90,50,85,45,55,390
71,우츠보트,Victreebel,grass,poison,80,105,65,100,70,70,490
72,왕눈해,Tentacool,water,poison,40,40,35,50,100,70,335
73,독파리,Tentacruel,water,poison,80,70,65,80,120,100,515
74,꼬마돌,Geodude,rock,ground,40,80,100,30,30,20,300
75,데구리,Graveler,rock,ground,55,95,115,45,45,35,390
76,딱구리,Golem,rock,ground,80,120,130,55,65,45,495
77,포니타,Ponyta,fire,,50,85,55,65,65,90,410
78,날쌩마,Rapidash,fire,,65,100,70,80,80,105,500
79,야돈,Slowpoke,water,psychic,90,65,65,40,40,15,315
80,야도란,Slowbro,water,psychic,95,75,110,100,80,30,490
81,코일,Magnemite,electric,steel,25,35,70,95,55,45,325
82,레어코일,Magneton,electric,steel,50,60,95,120,70,70,465
83,파오리,Farfetchd,normal,flying,52,90,55,58,62,60,377
84,두두,Doduo,normal,flying,35,85,45,35,35,75,310
85,두트리오,Dodrio,normal,flying,60,110,70,60,60,110,470
86,쥬쥬,Seel,water,,65,45,55,45,70,45,325
87,쥬레곤,Dewgong,water,ice,90,70,80,70,95,70,475
88,질퍽이,Grimer,poison,,80,80,50,40,50,25,325
89,질뻐기,Muk,poison,,105,105,75,65,100,50,500
90,셀러,Shellder,water,,30,65,100,45,25,40,305
91,파르셀,Cloyster,water,ice,50,95,180,85,45,70,525
92,고오스,Gastly,ghost,poison,30,35,30,100,35,80,310
93,고우스트,Haunter,ghost,poison,45,50,45,115,55,95,405
94,팬텀,Gengar,ghost,poison,60,65,60,130,75,110,500
95,롱스톤,Onix,rock,ground,35,45,160,30,45,70,385
96,슬리프,Drowzee,psychic,,60,48,45,43,90,42,328
97,슬리퍼,Hypno,psychic,,85,73,70,73,115,67,483
98,크랩,Krabby,water,,30,105,90,25,25,50,325
99,킹크랩,Kingler,water,,55,130,115,50,50,75,475
100,찌리리공,Voltorb,electric,,40,30,50,55,55,100,330
101,붐볼,Electrode,electric,,60,50,70,80,80,150,490
102,아라리,Exeggcute,grass,psychic,60,40,80,60,45,40,325
103,나시,Exeggutor,grass,psychic,95,95,85,125,75,55,530
104,탕구리,Cubone,ground,,50,50,95,40,50,35,320
105,텅구리A,Marowak,fire,ghost,60,80,110,50,80,45,425

106,시라소몬,Hitmonlee,fighting,,50,120,53,35,110,87,455
107,홍수몬,Hitmonchan,fighting,,50,105,79,35,110,76,455
108,내루미,Lickitung,normal,,90,55,75,60,75,30,385
109,또가스,Koffing,poison,,40,65,95,60,45,35,340
110,또도가스,Weezing,poison,,65,90,120,85,70,60,490
111,뿔카노,Rhyhorn,ground,rock,80,85,95,30,30,25,345
112,코뿌리,Rhydon,ground,rock,105,130,120,45,45,40,485
113,럭키,Chansey,normal,,250,5,5,35,105,50,450
114,덩쿠리,Tangela,grass,,65,55,115,100,40,60,435
115,캥카,Kangaskhan,normal,,105,95,80,40,80,90,490
116,쏘드라,Horsea,water,,30,40,70,70,25,60,295
117,시드라,Seadra,water,,55,65,95,95,45,85,440
118,콘치,Goldeen,water,,45,67,60,35,50,63,320
119,왕콘치,Seaking,water,,80,92,65,65,80,68,450
120,별가사리,Staryu,water,,30,45,55,70,55,85,340
121,아쿠스타,Starmie,water,psychic,60,75,85,100,85,115,520
122,마임맨,Mr-mime,psychic,fairy,40,45,65,100,120,90,460
123,스라크,Scyther,bug,flying,70,110,80,55,80,105,500
124,루주라,Jynx,ice,psychic,65,50,35,115,95,95,455
125,에레브,Electabuzz,electric,,65,83,57,95,85,105,490
126,마그마,Magmar,fire,,65,95,57,100,85,93,495
127,쁘사이저,Pinsir,bug,,65,125,100,55,70,85,500
128,켄타로스,Tauros,normal,,75,100,95,40,70,110,490
129,잉어킹,Magikarp,water,,20,10,55,15,20,80,200
130,갸라도스,Gyarados,water,flying,95,125,79,60,100,81,540
131,라프라스,Lapras,water,ice,130,85,80,85,95,60,535
132,메타몽,Ditto,normal,,48,48,48,48,48,48,288
133,이브이,Eevee,normal,,55,55,50,45,65,55,325
134,샤미드,Vaporeon,water,,130,65,60,110,95,65,525
135,쥬피썬더,Jolteon,electric,,65,65,60,110,95,130,525
136,부스터,Flareon,fire,,65,130,60,95,110,65,525
137,폴리곤,Porygon,normal,,65,60,70,85,75,40,395
138,암나이트,Omanyte,rock,water,35,40,100,90,55,35,355
139,암스타,Omastar,rock,water,70,60,125,115,70,55,495
140,투구,Kabuto,rock,water,30,80,90,55,45,55,355
141,투구푸스,Kabutops,rock,water,60,115,105,65,70,80,495
142,프테라,Aerodactyl,rock,flying,80,105,65,60,75,130,515
143,잠만보,Snorlax,normal,,160,110,65,65,110,30,540
144,프리져,Articuno,ice,flying,90,85,100,95,125,85,580
145,썬더,Zapdos,electric,flying,90,90,85,125,90,100,580
146,파이어,Moltres,fire,flying,90,100,90,125,85,90,580
147,미뇽,Dratini,dragon,,41,64,45,50,50,50,300
148,신뇽,Dragonair,dragon,,61,84,65,70,70,70,420
149,망나뇽,Dragonite,dragon,flying,91,134,95,100,100,80,600
150,뮤츠,Mewtwo,psychic,,106,110,90,154,90,130,680
151,뮤,Mew,psychic,,100,100,100,100,100,100,600
152,치코리타,Chikorita,grass,,45,49,65,49,65,45,318
153,베이리프,Bayleef,grass,,60,62,80,63,80,60,405
154,메가니움,Meganium,grass,,80,82,100,83,100,80,525
155,브케인,Cyndaquil,fire,,39,52,43,60,50,65,309
156,마그케인,Quilava,fire,,58,64,58,80,65,80,405
157,블레이범,Typhlosion,fire,,78,84,78,109,85,100,534
158,리아코,Totodile,water,,50,65,64,44,48,43,314
159,엘리게이,Croconaw,water,,65,80,80,59,63,58,405
160,장크로다일,Feraligatr,water,,85,105,100,79,83,78,530
161,꼬리선,Sentret,normal,,35,46,34,35,45,20,215
162,다꼬리,Furret,normal,,85,76,64,45,55,90,415
163,부우부,Hoothoot,normal,flying,60,30,30,36,56,50,262
164,야부엉,Noctowl,normal,flying,100,50,50,86,96,70,452
165,레디바,Ledyba,bug,flying,40,20,30,40,80,55,265
166,레디안,Ledian,bug,flying,55,35,50,55,110,85,390
167,페이검,Spinarak,bug,poison,40,60,40,40,40,30,250
168,아리아도스,Ariados,bug,poison,70,90,70,60,70,40,400
169,크로뱃,Crobat,poison,flying,85,90,80,70,80,130,535
170,초라기,Chinchou,water,electric,75,38,38,56,56,67,330
171,랜턴,Lanturn,water,electric,125,58,58,76,76,67,460
172,피츄,Pichu,electric,,20,40,15,35,35,60,205
173,삐,Cleffa,fairy,,50,25,28,45,55,15,218
174,푸푸린,Igglybuff,normal,fairy,90,30,15,40,20,15,210
175,토게피,Togepi,fairy,,35,20,65,40,65,20,245
176,토게틱,Togetic,fairy,flying,55,40,85,80,105,40,405
177,네이티,Natu,psychic,flying,40,50,45,70,45,70,320
178,네이티오,Xatu,psychic,flying,65,75,70,95,70,95,470
179,메리프,Mareep,electric,,55,40,40,65,45,35,280
180,보송송,Flaaffy,electric,,70,55,55,80,60,45,365
181,전룡,Ampharos,electric,,90,75,85,115,90,55,510
182,아르코,Bellossom,grass,,75,80,95,90,100,50,490
183,마릴,Marill,water,fairy,70,20,50,20,50,40,250
184,마릴리,Azumarill,water,fairy,100,50,80,60,80,50,420
185,꼬지모,Sudowoodo,rock,,70,100,115,30,65,30,410
186,왕구리,Politoed,water,,90,75,75,90,100,70,500
187,통통코,Hoppip,grass,flying,35,35,40,35,55,50,250
188,두코,Skiploom,grass,flying,55,45,50,45,65,80,340
189,솜솜코,Jumpluff,grass,flying,75,55,70,55,95,110,460
190,에이팜,Aipom,normal,,55,70,55,40,55,85,360
191,해너츠,Sunkern,grass,,30,30,30,30,30,30,180
192,해루미,Sunflora,grass,,75,75,55,105,85,30,425
193,왕자리,Yanma,bug,flying,65,65,45,75,45,95,390
194,우파,Wooper,water,ground,55,45,45,25,25,15,210
195,누오,Quagsire,water,ground,95,85,85,65,65,35,430
196,에브이,Espeon,psychic,,65,65,60,130,95,110,525
197,블래키,Umbreon,dark,,95,65,110,60,130,65,525
198,니로우,Murkrow,dark,flying,60,85,42,85,42,91,405
199,야도킹,Slowking,water,psychic,95,75,80,100,110,30,490
200,무우마,Misdreavus,ghost,,60,60,60,85,85,85,435
201,안농,Unown,psychic,,48,72,48,72,48,48,336
202,마자용,Wobbuffet,psychic,,190,33,58,33,58,33,405
203,키링키,Girafarig,normal,psychic,70,80,65,90,65,85,455
204,피콘,Pineco,bug,,50,65,90,35,35,15,290
205,쏘콘,Forretress,bug,steel,75,90,140,60,60,40,465
206,노고치,Dunsparce,normal,,100,70,70,65,65,45,415
207,글라이거,Gligar,ground,flying,65,75,105,35,65,85,430
208,강철톤,Steelix,steel,ground,75,85,200,55,65,30,510
209,블루,Snubbull,fairy,,60,80,50,40,40,30,300
210,그랑블루,Granbull,fairy,,90,120,75,60,60,45,450
211,침바루,Qwilfish,water,poison,65,95,85,55,55,85,440
212,핫삼,Scizor,bug,steel,70,130,100,55,80,65,500
213,단단지,Shuckle,bug,rock,20,10,230,10,230,5,505
214,헤라크로스,Heracross,bug,fighting,80,125,75,40,95,85,500
215,포푸니,Sneasel,dark,ice,55,95,55,35,75,115,430
216,깜지곰,Teddiursa,normal,,60,80,50,50,50,40,330
217,링곰,Ursaring,normal,,90,130,75,75,75,55,500
218,마그마그,Slugma,fire,,40,40,40,70,40,20,250
219,마그카르고,Magcargo,fire,rock,60,50,120,90,80,30,430
220,꾸꾸리,Swinub,ice,ground,50,50,40,30,30,50,250
221,메꾸리,Piloswine,ice,ground,100,100,80,60,60,50,450
222,코산호,Corsola,water,rock,65,55,95,65,95,35,410
223,총어,Remoraid,water,,35,65,35,65,35,65,300
224,대포무노,Octillery,water,,75,105,75,105,75,45,480
225,딜리버드,Delibird,ice,flying,45,55,45,65,45,75,330
226,만타인,Mantine,water,flying,85,40,70,80,140,70,485
227,무장조,Skarmory,steel,flying,65,80,140,40,70,70,465
228,델빌,Houndour,dark,fire,45,60,30,80,50,65,330
229,헬가,Houndoom,dark,fire,75,90,50,110,80,95,500
230,킹드라,Kingdra,water,dragon,75,95,95,95,95,85,540
231,코코리,Phanpy,ground,,90,60,60,40,40,40,330
232,코리갑,Donphan,ground,,90,120,120,60,60,50,500
233,폴리곤2,Porygon2,normal,,85,80,90,105,95,60,515
234,노라키,Stantler,normal,,73,95,62,85,65,85,465
235,루브도,Smeargle,normal,,55,20,35,20,45,75,250
236,배루키,Tyrogue,fighting,,35,35,35,35,35,35,210
237,카포에라,Hitmontop,fighting,,50,95,95,35,110,70,455
238,뽀뽀라,Smoochum,ice,psychic,45,30,15,85,65,65,305
239,에레키드,Elekid,electric,,45,63,37,65,55,95,360
240,마그비,Magby,fire,,45,75,37,70,55,83,365
241,밀탱크,Miltank,normal,,95,80,105,40,70,100,490
242,해피너스,Blissey,normal,,255,10,10,75,135,55,540
243,라이코,Raikou,electric,,90,85,75,115,100,115,580
244,앤테이,Entei,fire,,115,115,85,90,75,100,580
245,스이쿤,Suicune,water,,100,75,115,90,115,85,580
246,애버라스,Larvitar,rock,ground,50,64,50,45,50,41,300
247,데기라스,Pupitar,rock,ground,70,84,70,65,70,51,410
248,마기라스,Tyranitar,rock,dark,100,134,110,95,100,61,600
249,루기아,Lugia,psychic,flying,106,90,130,90,154,110,680
250,칠색조,Ho-oh,fire,flying,106,130,90,110,154,90,680
251,세레비,Celebi,psychic,grass,100,100,100,100,100,100,600
252,나무지기,Treecko,grass,,40,45,35,65,55,70,310
253,나무돌이,Grovyle,grass,,50,65,45,85,65,95,405
254,나무킹,Sceptile,grass,,70,85,65,105,85,120,530
255,아차모,Torchic,fire,,45,60,40,70,50,45,310
256,영치코,Combusken,fire,fighting,60,85,60,85,60,55,405
257,번치코,Blaziken,fire,fighting,80,120,70,110,70,80,530
258,물짱이,Mudkip,water,,50,70,50,50,50,40,310
259,늪짱이,Marshtomp,water,ground,70,85,70,60,70,50,405
260,대짱이,Swampert,water,ground,100,110,90,85,90,60,535
261,포챠나,Poochyena,dark,,35,55,35,30,30,35,220
262,그라에나,Mightyena,dark,,70,90,70,60,60,70,420
263,지그제구리,Zigzagoon,normal,,38,30,41,30,41,60,240
264,직구리,Linoone,normal,,78,70,61,50,61,100,420
265,개무소,Wurmple,bug,,45,45,35,20,30,20,195
266,실쿤,Silcoon,bug,,50,35,55,25,25,15,205
267,뷰티플라이,Beautifly,bug,flying,60,70,50,100,50,65,395
268,카스쿤,Cascoon,bug,,50,35,55,25,25,15,205
269,독케일,Dustox,bug,poison,60,50,70,50,90,65,385
270,연꽃몬,Lotad,water,grass,40,30,30,40,50,30,220
271,로토스,Lombre,water,grass,60,50,50,60,70,50,340
272,로파파,Ludicolo,water,grass,80,70,70,90,100,70,480
273,도토링,Seedot,grass,,40,40,50,30,30,30,220
274,잎새코,Nuzleaf,grass,dark,70,70,40,60,40,60,340
275,다탱구,Shiftry,grass,dark,90,100,60,90,60,80,480
276,테일로,Taillow,normal,flying,40,55,30,30,30,85,270
277,스왈로,Swellow,normal,flying,60,85,60,75,50,125,455
278,갈모매,Wingull,water,flying,40,30,30,55,30,85,270
279,패리퍼,Pelipper,water,flying,60,50,100,95,70,65,440
280,랄토스,Ralts,psychic,fairy,28,25,25,45,35,40,198
281,킬리아,Kirlia,psychic,fairy,38,35,35,65,55,50,278
282,가디안,Gardevoir,psychic,fairy,68,65,65,125,115,80,518
283,비구술,Surskit,bug,water,40,30,32,50,52,65,269
284,비나방,Masquerain,bug,flying,70,60,62,100,82,80,454
285,버섯꼬,Shroomish,grass,,60,40,60,40,60,35,295
286,버섯모,Breloom,grass,fighting,60,130,80,60,60,70,460
287,게을로,Slakoth,normal,,60,60,60,35,35,30,280
288,발바로,Vigoroth,normal,,80,80,80,55,55,90,440
289,게을킹,Slaking,normal,,150,160,100,95,65,100,670
290,토중몬,Nincada,bug,ground,31,45,90,30,30,40,266
291,아이스크,Ninjask,bug,flying,61,90,45,50,50,160,456
292,껍질몬,Shedinja,bug,ghost,1,90,45,30,30,40,236
293,소곤룡,Whismur,normal,,64,51,23,51,23,28,240
294,노공룡,Loudred,normal,,84,71,43,71,43,48,360
295,폭음룡,Exploud,normal,,104,91,63,91,73,68,490
296,마크탕,Makuhita,fighting,,72,60,30,20,30,25,237
297,하리뭉,Hariyama,fighting,,144,120,60,40,60,50,474
298,루리리,Azurill,normal,fairy,50,20,40,20,40,20,190
299,코코파스,Nosepass,rock,,30,45,135,45,90,30,375
300,에나비,Skitty,normal,,50,45,45,35,35,50,260
301,델케티,Delcatty,normal,,70,65,65,55,55,90,400
302,깜까미,Sableye,dark,ghost,50,75,75,65,65,50,380
303,입치트,Mawile,steel,fairy,50,85,85,55,55,50,380
304,가보리,Aron,steel,rock,50,70,100,40,40,30,330
305,갱도라,Lairon,steel,rock,60,90,140,50,50,40,430
306,보스로라,Aggron,steel,rock,70,110,180,60,60,50,530
307,요가랑,Meditite,fighting,psychic,30,40,55,40,55,60,280
308,요가램,Medicham,fighting,psychic,60,60,75,60,75,80,410
309,썬더라이,Electrike,electric,,40,45,40,65,40,65,295
310,썬더볼트,Manectric,electric,,70,75,60,105,60,105,475
311,플러시,Plusle,electric,,60,50,40,85,75,95,405
312,마이농,Minun,electric,,60,40,50,75,85,95,405
313,볼비트,Volbeat,bug,,65,73,75,47,85,85,430
314,네오비트,Illumise,bug,,65,47,75,73,85,85,430
315,로젤리아,Roselia,grass,poison,50,60,45,100,80,65,400
316,꼴깍몬,Gulpin,poison,,70,43,53,43,53,40,302
317,꿀꺽몬,Swalot,poison,,100,73,83,73,83,55,467
318,샤프니아,Carvanha,water,dark,45,90,20,65,20,65,305
319,샤크니아,Sharpedo,water,dark,70,120,40,95,40,95,460
320,고래왕자,Wailmer,water,,130,70,35,70,35,60,400
321,고래왕,Wailord,water,,170,90,45,90,45,60,500
322,둔타,Numel,fire,ground,60,60,40,65,45,35,305
323,폭타,Camerupt,fire,ground,70,100,70,105,75,40,460
324,코터스,Torkoal,fire,,70,85,140,85,70,20,470
325,피그점프,Spoink,psychic,,60,25,35,70,80,60,330
326,피그킹,Grumpig,psychic,,80,45,65,90,110,80,470
327,얼루기,Spinda,normal,,60,60,60,60,60,60,360
328,톱치,Trapinch,ground,,45,100,45,45,45,10,290
329,비브라바,Vibrava,ground,dragon,50,70,50,50,50,70,340
330,플라이곤,Flygon,ground,dragon,80,100,80,80,80,100,520
331,선인왕,Cacnea,grass,,50,85,40,85,40,35,335
332,밤선인,Cacturne,grass,dark,70,115,60,115,60,55,475
333,파비코,Swablu,normal,flying,45,40,60,40,75,50,310
334,파비코리,Altaria,dragon,flying,75,70,90,70,105,80,490
335,쟝고,Zangoose,normal,,73,115,60,60,60,90,458
336,세비퍼,Seviper,poison,,73,100,60,100,60,65,458
337,루나톤,Lunatone,rock,psychic,90,55,65,95,85,70,460
338,솔록,Solrock,rock,psychic,90,95,85,55,65,70,460
339,미꾸리,Barboach,water,ground,50,48,43,46,41,60,288
340,메깅,Whiscash,water,ground,110,78,73,76,71,60,468
341,가재군,Corphish,water,,43,80,65,50,35,35,308
342,가재장군,Crawdaunt,water,dark,63,120,85,90,55,55,468
343,오뚝군,Baltoy,ground,psychic,40,40,55,40,70,55,300
344,점토도리,Claydol,ground,psychic,60,70,105,70,120,75,500
345,릴링,Lileep,rock,grass,66,41,77,61,87,23,355
346,릴리요,Cradily,rock,grass,86,81,97,81,107,43,495
347,아노딥스,Anorith,rock,bug,45,95,50,40,50,75,355
348,아말도,Armaldo,rock,bug,75,125,100,70,80,45,495
349,빈티나,Feebas,water,,20,15,20,10,55,80,200
350,밀로틱,Milotic,water,,95,60,79,100,125,81,540
351,캐스퐁,Castform,normal,,70,70,70,70,70,70,420
352,켈리몬,Kecleon,normal,,60,90,70,60,120,40,440
353,어둠대신,Shuppet,ghost,,44,75,35,63,33,45,295
354,다크펫,Banette,ghost,,64,115,65,83,63,65,455
355,해골몽,Duskull,ghost,,20,40,90,30,90,25,295
356,미라몽,Dusclops,ghost,,40,70,130,60,130,25,455
357,트로피우스,Tropius,grass,flying,99,68,83,72,87,51,460
358,치렁,Chimecho,psychic,,75,50,80,95,90,65,455
359,앱솔,Absol,dark,,65,130,60,75,60,75,465
360,마자,Wynaut,psychic,,95,23,48,23,48,23,260
361,눈꼬마,Snorunt,ice,,50,50,50,50,50,50,300
362,얼음귀신,Glalie,ice,,80,80,80,80,80,80,480
363,대굴레오,Spheal,ice,water,70,40,50,55,50,25,290
364,씨레오,Sealeo,ice,water,90,60,70,75,70,45,410
365,씨카이저,Walrein,ice,water,110,80,90,95,90,65,530
366,진주몽,Clamperl,water,,35,64,85,74,55,32,345
367,헌테일,Huntail,water,,55,104,105,94,75,52,485
368,분홍장이,Gorebyss,water,,55,84,105,114,75,52,485
369,시라칸,Relicanth,water,rock,100,90,130,45,65,55,485
370,사랑동이,Luvdisc,water,,43,30,55,40,65,97,330
371,아공이,Bagon,dragon,,45,75,60,40,30,50,300
372,쉘곤,Shelgon,dragon,,65,95,100,60,50,50,420
373,보만다,Salamence,dragon,flying,95,135,80,110,80,100,600
374,메탕,Beldum,steel,psychic,40,55,80,35,60,30,300
375,메탕구,Metang,steel,psychic,60,75,100,55,80,50,420
376,메타그로스,Metagross,steel,psychic,80,135,130,95,90,70,600
377,레지락,Regirock,rock,,80,100,200,50,100,50,580
378,레지아이스,Regice,ice,,80,50,100,100,200,50,580
379,레지스틸,Registeel,steel,,80,75,150,75,150,50,580
380,라티아스,Latias,dragon,psychic,80,80,90,110,130,110,600
381,라티오스,Latios,dragon,psychic,80,90,80,130,110,110,600
382,가이오가,Kyogre,water,,100,100,90,150,140,90,670
383,그란돈,Groudon,ground,,100,150,140,100,90,90,670
384,레쿠쟈,Rayquaza,dragon,flying,105,150,90,150,90,95,680
385,지라치,Jirachi,steel,psychic,100,100,100,100,100,100,600
386,테오키스,Deoxys-normal,psychic,,50,150,50,150,50,150,600
387,모부기,Turtwig,grass,,55,68,64,45,55,31,318
388,수풀부기,Grotle,grass,,75,89,85,55,65,36,405
389,토대부기,Torterra,grass,ground,95,109,105,75,85,56,525
390,불꽃숭이,Chimchar,fire,,44,58,44,58,44,61,309
391,파이숭이,Monferno,fire,fighting,64,78,52,78,52,81,405
392,초염몽,Infernape,fire,fighting,76,104,71,104,71,108,534
393,팽도리,Piplup,water,,53,51,53,61,56,40,314
394,팽태자,Prinplup,water,,64,66,68,81,76,50,405
395,엠페르트,Empoleon,water,steel,84,86,88,111,101,60,530
396,찌르꼬,Starly,normal,flying,40,55,30,30,30,60,245
397,찌르버드,Staravia,normal,flying,55,75,50,40,40,80,340
398,찌르호크,Staraptor,normal,flying,85,120,70,50,60,100,485
399,비버니,Bidoof,normal,,59,45,40,35,40,31,250
400,비버통,Bibarel,normal,water,79,85,60,55,60,71,410
401,귀뚤뚜기,Kricketot,bug,,37,25,41,25,41,25,194
402,귀뚤톡크,Kricketune,bug,,77,85,51,55,51,65,384
403,꼬링크,Shinx,electric,,45,65,34,40,34,45,263
404,럭시오,Luxio,electric,,60,85,49,60,49,60,363
405,렌트라,Luxray,electric,,80,120,79,95,79,70,523
406,꼬몽울,Budew,grass,poison,40,30,35,50,70,55,280
407,로즈레이드,Roserade,grass,poison,60,70,65,125,105,90,515
408,두개도스,Cranidos,rock,,67,125,40,30,30,58,350
409,램펄드,Rampardos,rock,,97,165,60,65,50,58,495
410,방패톱스,Shieldon,rock,steel,30,42,118,42,88,30,350
411,바리톱스,Bastiodon,rock,steel,60,52,168,47,138,30,495
412,도롱충이,Burmy,bug,,40,29,45,29,45,36,224
413,도롱마담,Wormadam-plant,bug,grass,60,59,85,79,105,36,424
414,나메일,Mothim,bug,flying,70,94,50,94,50,66,424
415,세꿀버리,Combee,bug,flying,30,30,42,30,42,70,244
416,비퀸,Vespiquen,bug,flying,70,80,102,80,102,40,474
417,파치리스,Pachirisu,electric,,60,45,70,45,90,95,405
418,브이젤,Buizel,water,,55,65,35,60,30,85,330
419,플로젤,Floatzel,water,,85,105,55,85,50,115,495
420,체리버,Cherubi,grass,,45,35,45,62,53,35,275
421,체리꼬,Cherrim,grass,,70,60,70,87,78,85,450
422,깝질무,Shellos,water,,76,48,48,57,62,34,325
423,트리토돈,Gastrodon,water,ground,111,83,68,92,82,39,475
424,겟핸보숭,Ambipom,normal,,75,100,66,60,66,115,482
425,흔들풍손,Drifloon,ghost,flying,90,50,34,60,44,70,348
426,둥실라이드,Drifblim,ghost,flying,150,80,44,90,54,80,498
427,이어롤,Buneary,normal,,55,66,44,44,56,85,350
428,이어롭,Lopunny,normal,,65,76,84,54,96,105,480
429,무우마직,Mismagius,ghost,,60,60,60,105,105,105,495
430,돈크로우,Honchkrow,dark,flying,100,125,52,105,52,71,505
431,나옹마,Glameow,normal,,49,55,42,42,37,85,310
432,몬냥이,Purugly,normal,,71,82,64,64,59,112,452
433,랑딸랑,Chingling,psychic,,45,30,50,65,50,45,285
434,스컹뿡,Stunky,poison,dark,63,63,47,41,41,74,329
435,스컹탱크,Skuntank,poison,dark,103,93,67,71,61,84,479
436,동미러,Bronzor,steel,psychic,57,24,86,24,86,23,300
437,동탁군,Bronzong,steel,psychic,67,89,116,79,116,33,500
438,꼬지지,Bonsly,rock,,50,80,95,10,45,10,290
439,흉내내,Mime-jr,psychic,fairy,20,25,45,70,90,60,310
440,핑복,Happiny,normal,,100,5,5,15,65,30,220
441,페라페,Chatot,normal,flying,76,65,45,92,42,91,411
442,화강돌,Spiritomb,ghost,dark,50,92,108,92,108,35,485
443,딥상어동,Gible,dragon,ground,58,70,45,40,45,42,300
444,한바이트,Gabite,dragon,ground,68,90,65,50,55,82,410
445,한카리아스,Garchomp,dragon,ground,108,130,95,80,85,102,600
446,먹고자,Munchlax,normal,,135,85,40,40,85,5,390
447,리오르,Riolu,fighting,,40,70,40,35,40,60,285
448,루카리오,Lucario,fighting,steel,70,110,70,115,70,90,525
449,히포포타스,Hippopotas,ground,,68,72,78,38,42,32,330
450,하마돈,Hippowdon,ground,,108,112,118,68,72,47,525
451,스콜피,Skorupi,poison,bug,40,50,90,30,55,65,330
452,드래피온,Drapion,poison,dark,70,90,110,60,75,95,500
453,삐딱구리,Croagunk,poison,fighting,48,61,40,61,40,50,300
454,독개굴,Toxicroak,poison,fighting,83,106,65,86,65,85,490
455,무스틈니,Carnivine,grass,,74,100,72,90,72,46,454
456,형광어,Finneon,water,,49,49,56,49,61,66,330
457,네오라이트,Lumineon,water,,69,69,76,69,86,91,460
458,타만타,Mantyke,water,flying,45,20,50,60,120,50,345
459,눈쓰개,Snover,grass,ice,60,62,50,62,60,40,334
460,눈설왕,Abomasnow,grass,ice,90,92,75,92,85,60,494
461,포푸니라,Weavile,dark,ice,70,120,65,45,85,125,510
462,자포코일,Magnezone,electric,steel,70,70,115,130,90,60,535
463,내룸벨트,Lickilicky,normal,,110,85,95,80,95,50,515
464,거대코뿌리,Rhyperior,ground,rock,115,140,130,55,55,40,535
465,덩쿠림보,Tangrowth,grass,,100,100,125,110,50,50,535
466,에레키블,Electivire,electric,,75,123,67,95,85,95,540
467,마그마번,Magmortar,fire,,75,95,67,125,95,83,540
468,토게키스,Togekiss,fairy,flying,85,50,95,120,115,80,545
469,메가자리,Yanmega,bug,flying,86,76,86,116,56,95,515
470,리피아,Leafeon,grass,,65,110,130,60,65,95,525
471,글레이시아,Glaceon,ice,,65,60,110,130,95,65,525
472,글라이온,Gliscor,ground,flying,75,95,125,45,75,95,510
473,맘모꾸리,Mamoswine,ice,ground,110,130,80,70,60,80,530
474,폴리곤Z,Porygon-z,normal,,85,80,70,135,75,90,535
475,엘레이드,Gallade,psychic,fighting,68,125,65,65,115,80,518
476,대코파스,Probopass,rock,steel,60,55,145,75,150,40,525
477,야느와르몽,Dusknoir,ghost,,45,100,135,65,135,45,525
478,눈여아,Froslass,ice,ghost,70,80,70,80,70,110,480
479,F로토무,Rotom,electric,ice,50,65,107,105,107,86,520
480,유크시,Uxie,psychic,,75,75,130,75,130,95,580
481,엠라이트,Mesprit,psychic,,80,105,105,105,105,80,580
482,아그놈,Azelf,psychic,,75,125,70,125,70,115,580
483,디아루가,Dialga,steel,dragon,100,120,120,150,100,90,680
484,펄기아,Palkia,water,dragon,90,120,100,150,120,100,680
485,히드런,Heatran,fire,steel,91,90,106,130,106,77,600
486,레지기가스,Regigigas,normal,,110,160,110,80,110,100,670
487,기라티나,Giratina-altered,ghost,dragon,150,100,120,100,120,90,680
488,크레세리아,Cresselia,psychic,,120,70,110,75,120,85,580
489,피오네,Phione,water,,80,80,80,80,80,80,480
490,마나피,Manaphy,water,,100,100,100,100,100,100,600
491,다크라이,Darkrai,dark,,70,90,90,135,90,125,600
492,쉐이미,Shaymin-land,grass,,100,100,100,100,100,100,600
493,아르세우스,Arceus,normal,,120,120,120,120,120,120,720
494,비크티니,Victini,psychic,fire,100,100,100,100,100,100,600
495,주리비얀,Snivy,grass,,45,45,55,45,55,63,308
496,샤비,Servine,grass,,60,60,75,60,75,83,413
497,샤로다,Serperior,grass,,75,75,95,75,95,113,528
498,뚜꾸리,Tepig,fire,,65,63,45,45,45,45,308
499,차오꿀,Pignite,fire,fighting,90,93,55,70,55,55,418
500,염무왕,Emboar,fire,fighting,110,123,65,100,65,65,528
501,수댕이,Oshawott,water,,55,55,45,63,45,45,308
502,쌍검자비,Dewott,water,,75,75,60,83,60,60,413
503,대검귀,Samurott,water,,95,100,85,108,70,70,528
504,보르쥐,Patrat,normal,,45,55,39,35,39,42,255
505,보르그,Watchog,normal,,60,85,69,60,69,77,420
506,요테리,Lillipup,normal,,45,60,45,25,45,55,275
507,하데리어,Herdier,normal,,65,80,65,35,65,60,370
508,바랜드,Stoutland,normal,,85,110,90,45,90,80,500
509,쌔비냥,Purrloin,dark,,41,50,37,50,37,66,281
510,레파르다스,Liepard,dark,,64,88,50,88,50,106,446
511,야나프,Pansage,grass,,50,53,48,53,48,64,316
512,야나키,Simisage,grass,,75,98,63,98,63,101,498
513,바오프,Pansear,fire,,50,53,48,53,48,64,316
514,바오키,Simisear,fire,,75,98,63,98,63,101,498
515,앗차프,Panpour,water,,50,53,48,53,48,64,316
516,앗차키,Simipour,water,,75,98,63,98,63,101,498
517,몽나,Munna,psychic,,76,25,45,67,55,24,292
518,몽얌나,Musharna,psychic,,116,55,85,107,95,29,487
519,콩둘기,Pidove,normal,flying,50,55,50,36,30,43,264
520,유토브,Tranquill,normal,flying,62,77,62,50,42,65,358
521,켄호로우,Unfezant,normal,flying,80,115,80,65,55,93,488
522,줄뮤마,Blitzle,electric,,45,60,32,50,32,76,295
523,제브라이카,Zebstrika,electric,,75,100,63,80,63,116,497
524,단굴,Roggenrola,rock,,55,75,85,25,25,15,280
525,암트르,Boldore,rock,,70,105,105,50,40,20,390
526,기가이어스,Gigalith,rock,,85,135,130,60,80,25,515
527,또르박쥐,Woobat,psychic,flying,65,45,43,55,43,72,323
528,맘박쥐,Swoobat,psychic,flying,67,57,55,77,55,114,425
529,두더류,Drilbur,ground,,60,85,40,30,45,68,328
530,몰드류,Excadrill,ground,steel,110,135,60,50,65,88,508
531,다부니,Audino,normal,,103,60,86,60,86,50,445
532,으랏차,Timburr,fighting,,75,80,55,25,35,35,305
533,토쇠골,Gurdurr,fighting,,85,105,85,40,50,40,405
534,노보청,Conkeldurr,fighting,,105,140,95,55,65,45,505
535,동챙이,Tympole,water,,50,50,40,50,40,64,294
536,두까비,Palpitoad,water,ground,75,65,55,65,55,69,384
537,두빅굴,Seismitoad,water,ground,105,95,75,85,75,74,509
538,던지미,Throh,fighting,,120,100,85,30,85,45,465
539,타격귀,Sawk,fighting,,75,125,75,30,75,85,465
540,두르보,Sewaddle,bug,grass,45,53,70,40,60,42,310
541,두르쿤,Swadloon,bug,grass,55,63,90,50,80,42,380
542,모아머,Leavanny,bug,grass,75,103,80,70,80,92,500
543,마디네,Venipede,bug,poison,30,45,59,30,39,57,260
544,휠구,Whirlipede,bug,poison,40,55,99,40,79,47,360
545,펜드라,Scolipede,bug,poison,60,100,89,55,69,112,485
546,소미안,Cottonee,grass,fairy,40,27,60,37,50,66,280
547,엘풍,Whimsicott,grass,fairy,60,67,85,77,75,116,480
548,치릴리,Petilil,grass,,45,35,50,70,50,30,280
549,드레디어,Lilligant,grass,,70,60,75,110,75,90,480
550,배쓰나이,Basculin-red-striped,water,,70,92,65,80,55,98,460
551,깜눈크,Sandile,ground,dark,50,72,35,35,35,65,292
552,악비르,Krokorok,ground,dark,60,82,45,45,45,74,351
553,악비아르,Krookodile,ground,dark,95,117,80,65,70,92,519
554,달막화,Darumaka,fire,,70,90,45,15,45,50,315
555,불비달마,Darmanitan-standard,fire,,105,140,55,30,55,95,480
556,마라카치,Maractus,grass,,75,86,67,106,67,60,461
557,돌살이,Dwebble,bug,rock,50,65,85,35,35,55,325
558,암팰리스,Crustle,bug,rock,70,105,125,65,75,45,485
559,곤율랭,Scraggy,dark,fighting,50,75,70,35,70,48,348
560,곤율거니,Scrafty,dark,fighting,65,90,115,45,115,58,488
561,심보러,Sigilyph,psychic,flying,72,58,80,103,80,97,490
562,데스마스,Yamask,ghost,,38,30,85,55,65,30,303
563,데스니칸,Cofagrigus,ghost,,58,50,145,95,105,30,483
564,프로토가,Tirtouga,water,rock,54,78,103,53,45,22,355
565,늑골라,Carracosta,water,rock,74,108,133,83,65,32,495
566,아켄,Archen,rock,flying,55,112,45,74,45,70,401
567,아케오스,Archeops,rock,flying,75,140,65,112,65,110,567
568,깨봉이,Trubbish,poison,,50,50,62,40,62,65,329
569,더스트나,Garbodor,poison,,80,95,82,60,82,75,474
570,조로아,Zorua,dark,,40,65,40,80,40,65,330
571,조로아크,Zoroark,dark,,60,105,60,120,60,105,510
572,치라미,Minccino,normal,,55,50,40,40,40,75,300
573,치라치노,Cinccino,normal,,75,95,60,65,60,115,470
574,고디탱,Gothita,psychic,,45,30,50,55,65,45,290
575,고디보미,Gothorita,psychic,,60,45,70,75,85,55,390
576,고디모아젤,Gothitelle,psychic,,70,55,95,95,110,65,490
577,유니란,Solosis,psychic,,45,30,40,105,50,20,290
578,듀란,Duosion,psychic,,65,40,50,125,60,30,370
579,란쿨루스,Reuniclus,psychic,,110,65,75,125,85,30,490
580,꼬지보리,Ducklett,water,flying,62,44,50,44,50,55,305
581,스완나,Swanna,water,flying,75,87,63,87,63,98,473
582,바닐프티,Vanillite,ice,,36,50,50,65,60,44,305
583,바닐리치,Vanillish,ice,,51,65,65,80,75,59,395
584,배바닐라,Vanilluxe,ice,,71,95,85,110,95,79,535
585,사철록,Deerling,normal,grass,60,60,50,40,50,75,335
586,바라철록,Sawsbuck,normal,grass,80,100,70,60,70,95,475
587,에몽가,Emolga,electric,flying,55,75,60,75,60,103,428
588,딱정곤,Karrablast,bug,,50,75,45,40,45,60,315
589,슈바르고,Escavalier,bug,steel,70,135,105,60,105,20,495
590,깜놀버슬,Foongus,grass,poison,69,55,45,55,55,15,294
591,뽀록나,Amoonguss,grass,poison,114,85,70,85,80,30,464
592,탱그릴,Frillish-male,water,ghost,55,40,50,65,85,40,335
593,탱탱겔,Jellicent-male,water,ghost,100,60,70,85,105,60,480
594,맘복치,Alomomola,water,,165,75,80,40,45,65,470
595,파쪼옥,Joltik,bug,electric,50,47,50,57,50,65,319
596,전툴라,Galvantula,bug,electric,70,77,60,97,60,108,472
597,철시드,Ferroseed,grass,steel,44,50,91,24,86,10,305
598,너트령,Ferrothorn,grass,steel,74,94,131,54,116,20,489
599,기어르,Klink,steel,,40,55,70,45,60,30,300
600,기기어르,Klang,steel,,60,80,95,70,85,50,440
601,기기기어르,Klinklang,steel,,60,100,115,70,85,90,520
602,저리어,Tynamo,electric,,35,55,40,45,40,60,275
603,저리릴,Eelektrik,electric,,65,85,70,75,70,40,405
604,저리더프,Eelektross,electric,,85,115,80,105,80,50,515
605,리그레,Elgyem,psychic,,55,55,55,85,55,30,335
606,벰크,Beheeyem,psychic,,75,75,75,125,95,40,485
607,불켜미,Litwick,ghost,fire,50,30,55,65,55,20,275
608,램프라,Lampent,ghost,fire,60,40,60,95,60,55,370
609,샹델라,Chandelure,ghost,fire,60,55,90,145,90,80,520
610,터검니,Axew,dragon,,46,87,60,30,40,57,320
611,액슨도,Fraxure,dragon,,66,117,70,40,50,67,410
612,액스라이즈,Haxorus,dragon,,76,147,90,60,70,97,540
613,코고미,Cubchoo,ice,,55,70,40,60,40,40,305
614,툰베어,Beartic,ice,,95,130,80,70,80,50,505
615,프리지오,Cryogonal,ice,,80,50,50,95,135,105,515
616,쪼마리,Shelmet,bug,,50,40,85,40,65,25,305
617,어지리더,Accelgor,bug,,80,70,40,100,60,145,495
618,메더,Stunfisk,ground,electric,109,66,84,81,99,32,471
619,비조푸,Mienfoo,fighting,,45,85,50,55,50,65,350
620,비조도,Mienshao,fighting,,65,125,60,95,60,105,510
621,크리만,Druddigon,dragon,,77,120,90,60,90,48,485
622,골비람,Golett,ground,ghost,59,74,50,35,50,35,303
623,골루그,Golurk,ground,ghost,89,124,80,55,80,55,483
624,자망칼,Pawniard,dark,steel,45,85,70,40,40,60,340
625,절각참,Bisharp,dark,steel,65,125,100,60,70,70,490
626,버프론,Bouffalant,normal,,95,110,95,40,95,55,490
627,수리둥보,Rufflet,normal,flying,70,83,50,37,50,60,350
628,워글,Braviary,normal,flying,100,123,75,57,75,80,510
629,벌차이,Vullaby,dark,flying,70,55,75,45,65,60,370
630,버랜지나,Mandibuzz,dark,flying,110,65,105,55,95,80,510
631,앤티골,Heatmor,fire,,85,97,66,105,66,65,484
632,아이앤트,Durant,bug,steel,58,109,112,48,48,109,484
633,모노두,Deino,dark,dragon,52,65,50,45,50,38,300
634,디헤드,Zweilous,dark,dragon,72,85,70,65,70,58,420
635,삼삼드래,Hydreigon,dark,dragon,92,105,90,125,90,98,600
636,활화르바,Larvesta,bug,fire,55,85,55,50,55,60,360
637,불카모스,Volcarona,bug,fire,85,60,65,135,105,100,550
638,코바르온,Cobalion,steel,fighting,91,90,129,90,72,108,580
639,테라키온,Terrakion,rock,fighting,91,129,90,72,90,108,580
640,비리디온,Virizion,grass,fighting,91,90,72,90,129,108,580
641,토네로스,Tornadus-incarnate,flying,,79,115,70,125,80,111,580
642,볼트로스,Thundurus-incarnate,electric,flying,79,115,70,125,80,111,580
643,레시라무,Reshiram,dragon,fire,100,120,100,150,120,90,680
644,제크로무,Zekrom,dragon,electric,100,150,120,120,100,90,680
645,랜드로스,Landorus-incarnate,ground,flying,89,125,90,115,80,101,600
646,큐레무,Kyurem,dragon,ice,125,130,90,130,90,95,660
647,케르디오,Keldeo-ordinary,water,fighting,91,72,90,129,90,108,580
648,메로엣타,Meloetta-aria,normal,psychic,100,77,77,128,128,90,600
649,게노세크트,Genesect,bug,steel,71,120,95,120,95,99,600
650,도치마론,Chespin,grass,,56,61,65,48,45,38,313
651,도치보구,Quilladin,grass,,61,78,95,56,58,57,405
652,브리가론,Chesnaught,grass,fighting,88,107,122,74,75,64,530
653,푸호꼬,Fennekin,fire,,40,45,40,62,60,60,307
654,테르나,Braixen,fire,,59,59,58,90,70,73,409
655,마폭시,Delphox,fire,psychic,75,69,72,114,100,104,534
656,개구마르,Froakie,water,,41,56,40,62,44,71,314
657,개굴반장,Frogadier,water,,54,63,52,83,56,97,405
658,개굴닌자,Greninja,water,dark,72,95,67,103,71,122,530
659,파르빗,Bunnelby,normal,,38,36,38,32,36,57,237
660,파르토,Diggersby,normal,ground,85,56,77,50,77,78,423
661,화살꼬빈,Fletchling,normal,flying,45,50,43,40,38,62,278
662,불화살빈,Fletchinder,fire,flying,62,73,55,56,52,84,382
663,파이어로,Talonflame,fire,flying,78,81,71,74,69,126,499
664,분이벌레,Scatterbug,bug,,38,35,40,27,25,35,200
665,분떠도리,Spewpa,bug,,45,22,60,27,30,29,213
666,비비용,Vivillon,bug,flying,80,52,50,90,50,89,411
667,레오꼬,Litleo,fire,normal,62,50,58,73,54,72,369
668,화염레오,Pyroar-male,fire,normal,86,68,72,109,66,106,507
669,플라베베,Flabebe,fairy,,44,38,39,61,79,42,303
670,플라엣테,Floette,fairy,,54,45,47,75,98,52,371
671,플라제스,Florges,fairy,,78,65,68,112,154,75,552
672,메이클,Skiddo,grass,,66,65,48,62,57,52,350
673,고고트,Gogoat,grass,,123,100,62,97,81,68,531
674,판짱,Pancham,fighting,,67,82,62,46,48,43,348
675,부란다,Pangoro,fighting,dark,95,124,78,69,71,58,495
676,트리미앙,Furfrou,normal,,75,80,60,65,90,102,472
677,냐스퍼,Espurr,psychic,,62,48,54,63,60,68,355
678,냐오닉스,Meowstic-male,psychic,,74,48,76,83,81,104,466
679,단칼빙,Honedge,steel,ghost,45,80,100,35,37,28,325
680,쌍검킬,Doublade,steel,ghost,59,110,150,45,49,35,448
681,킬가르도,Aegislash-shield,steel,ghost,60,50,140,50,140,60,500
682,슈쁘,Spritzee,fairy,,78,52,60,63,65,23,341
683,프레프티르,Aromatisse,fairy,,101,72,72,99,89,29,462
684,나룸퍼프,Swirlix,fairy,,62,48,66,59,57,49,341
685,나루림,Slurpuff,fairy,,82,80,86,85,75,72,480
686,오케이징,Inkay,dark,psychic,53,54,53,37,46,45,288
687,칼라마네로,Malamar,dark,psychic,86,92,88,68,75,73,482
688,거북손손,Binacle,rock,water,42,52,67,39,56,50,306
689,거북손데스,Barbaracle,rock,water,72,105,115,54,86,68,500
690,수레기,Skrelp,poison,water,50,60,60,60,60,30,320
691,드래캄,Dragalge,poison,dragon,65,75,90,97,123,44,494
692,완철포,Clauncher,water,,50,53,62,58,63,44,330
693,블로스터,Clawitzer,water,,71,73,88,120,89,59,500
694,목도리키텔,Helioptile,electric,normal,44,38,33,61,43,70,289
695,일레도리자드,Heliolisk,electric,normal,62,55,52,109,94,109,481
696,티고라스,Tyrunt,rock,dragon,58,89,77,45,45,48,362
697,견고라스,Tyrantrum,rock,dragon,82,121,119,69,59,71,521
698,아마루스,Amaura,rock,ice,77,59,50,67,63,46,362
699,아마루르가,Aurorus,rock,ice,123,77,72,99,92,58,521
700,님피아,Sylveon,fairy,,95,65,65,110,130,60,525
701,루차불,Hawlucha,fighting,flying,78,92,75,74,63,118,500
702,데덴네,Dedenne,electric,fairy,67,58,57,81,67,101,431
703,멜리시,Carbink,rock,fairy,50,50,150,50,150,50,500
704,미끄메라,Goomy,dragon,,45,50,35,55,75,40,300
705,미끄네일,Sliggoo,dragon,,68,75,53,83,113,60,452
706,미끄래곤,Goodra,dragon,,90,100,70,110,150,80,600
707,클레피,Klefki,steel,fairy,57,80,91,80,87,75,470
708,나목령,Phantump,ghost,grass,43,70,48,50,60,38,309
709,대로트,Trevenant,ghost,grass,85,110,76,65,82,56,474
710,호바귀,Pumpkaboo-average,ghost,grass,49,66,70,44,55,51,335
711,펌킨인,Gourgeist-average,ghost,grass,65,90,122,58,75,84,494
712,꽁어름,Bergmite,ice,,55,69,85,32,35,28,304
713,크레베이스,Avalugg,ice,,95,117,184,44,46,28,514
714,음뱃,Noibat,flying,dragon,40,30,35,45,40,55,245
715,음번,Noivern,flying,dragon,85,70,80,97,80,123,535
716,제르네아스,Xerneas,fairy,,126,131,95,131,98,99,680
717,이벨타르,Yveltal,dark,flying,126,131,95,131,98,99,680
718,지가르데,Zygarde-50,dragon,ground,108,100,121,81,95,95,600
719,디안시,Diancie,rock,fairy,50,100,150,100,150,50,600
720,후파,Hoopa,psychic,ghost,80,110,60,150,130,70,600
721,볼케니온,Volcanion,fire,water,80,110,120,130,90,70,600
722,나몰빼미,Rowlet,grass,flying,68,55,55,50,50,42,320
723,빼미스로우,Dartrix,grass,flying,78,75,75,70,70,52,420
724,모크나이퍼,Decidueye,grass,ghost,78,107,75,100,100,70,530
725,냐오불,Litten,fire,,45,65,40,60,40,70,320
726,냐오히트,Torracat,fire,,65,85,50,80,50,90,420
727,어흥염,Incineroar,fire,dark,95,115,90,80,90,60,530
728,누리공,Popplio,water,,50,54,54,66,56,40,320
729,키요공,Brionne,water,,60,69,69,91,81,50,420
730,누리레느,Primarina,water,fairy,80,74,74,126,116,60,530
731,콕코구리,Pikipek,normal,flying,35,75,30,30,30,65,265
732,크라파,Trumbeak,normal,flying,55,85,50,40,50,75,355
733,왕큰부리,Toucannon,normal,flying,80,120,75,75,75,60,485
734,영구스,Yungoos,normal,,48,70,30,30,30,45,253
735,형사구스,Gumshoos,normal,,88,110,60,55,60,45,418
736,턱지충이,Grubbin,bug,,47,62,45,55,45,46,300
737,전지충이,Charjabug,bug,electric,57,82,95,55,75,36,400
738,투구뿌논,Vikavolt,bug,electric,77,70,90,145,75,43,500
739,오기지게,Crabrawler,fighting,,47,82,57,42,47,63,338
740,모단단게,Crabominable,fighting,ice,97,132,77,62,67,43,478
741,춤추새훌라,Oricorio-baile,psychic,flying,75,70,70,98,70,93,476
742,에블리,Cutiefly,bug,fairy,40,45,40,55,40,84,304
743,에리본,Ribombee,bug,fairy,60,55,60,95,70,124,464
744,암멍이,Rockruff,rock,,45,65,40,30,40,60,280
745,루가루암,Lycanroc-midday,rock,,75,115,65,55,65,112,487
746,약어리,Wishiwashi-solo,water,,45,20,20,25,25,40,175
747,시마사리,Mareanie,poison,water,50,53,62,43,52,45,305
748,더시마사리,Toxapex,poison,water,50,63,152,53,142,35,495
749,머드나기,Mudbray,ground,,70,100,70,45,55,45,385
750,만마드,Mudsdale,ground,,100,125,100,55,85,35,500
751,물거미,Dewpider,water,bug,38,40,52,40,72,27,269
752,깨비물거미,Araquanid,water,bug,68,70,92,50,132,42,454
753,짜랑랑,Fomantis,grass,,40,55,35,50,35,35,250
754,라란티스,Lurantis,grass,,70,105,90,80,90,45,480
755,자마슈,Morelull,grass,fairy,40,35,55,65,75,15,285
756,마셰이드,Shiinotic,grass,fairy,60,45,80,90,100,30,405
757,야도뇽,Salandit,poison,fire,48,44,40,71,40,77,320
758,염뉴트,Salazzle,poison,fire,68,64,60,111,60,117,480
759,포곰곰,Stufful,normal,fighting,70,75,50,45,50,50,340
760,이븐곰,Bewear,normal,fighting,120,125,80,55,60,60,500
761,달콤아,Bounsweet,grass,,42,30,38,30,38,32,210
762,달무리나,Steenee,grass,,52,40,48,40,48,62,290
763,달코퀸,Tsareena,grass,,72,120,98,50,98,72,510
764,큐아링,Comfey,fairy,,51,52,90,82,110,100,485
765,하랑우탄,Oranguru,normal,psychic,90,60,80,90,110,60,490
766,내던숭이,Passimian,fighting,,100,120,90,40,60,80,490
767,꼬시레,Wimpod,bug,water,25,35,40,20,30,80,230
768,갑주무사,Golisopod,bug,water,75,125,140,60,90,40,530
769,모래꿍,Sandygast,ghost,ground,55,55,80,70,45,15,320
770,모래성이당,Palossand,ghost,ground,85,75,110,100,75,35,480
771,해무기,Pyukumuku,water,,55,60,130,30,130,5,410
772,타입:널,Type-null,normal,,95,95,95,95,95,59,534
773,실버디,Silvally,normal,,95,95,95,95,95,95,570
774,메테노,Minior-red-meteor,rock,flying,60,60,100,60,100,60,440
775,자말라,Komala,normal,,65,115,65,75,95,65,480
776,폭거북스,Turtonator,fire,dragon,60,78,135,91,85,36,485
777,토게데마루,Togedemaru,electric,steel,65,98,63,40,73,96,435
778,따라큐,Mimikyu-disguised,ghost,fairy,55,90,80,50,105,96,476
779,치갈기,Bruxish,water,psychic,68,105,70,70,70,92,475
780,할비롱,Drampa,normal,dragon,78,60,85,135,91,36,485
781,타타륜,Dhelmise,ghost,grass,70,131,100,86,90,40,517
782,짜랑꼬,Jangmo-o,dragon,,45,55,65,45,45,45,300
783,짜랑고우,Hakamo-o,dragon,fighting,55,75,90,65,70,65,420
784,짜랑고우거,Kommo-o,dragon,fighting,75,110,125,100,105,85,600
785,카푸꼬꼬꼭,Tapu-koko,electric,fairy,70,115,85,95,75,130,570
786,카푸나비나,Tapu-lele,psychic,fairy,70,85,75,130,115,95,570
787,카푸브루루,Tapu-bulu,grass,fairy,70,130,115,85,95,75,570
788,카푸느지느,Tapu-fini,water,fairy,70,75,115,95,130,85,570
789,코스모그,Cosmog,psychic,,43,29,31,29,31,37,200
790,코스모움,Cosmoem,psychic,,43,29,131,29,131,37,400
791,솔가레오,Solgaleo,psychic,steel,137,137,107,113,89,97,680
792,루나아라,Lunala,psychic,ghost,137,113,89,137,107,97,680
793,텅비드,Nihilego,rock,poison,109,53,47,127,131,103,570
794,매시붕,Buzzwole,bug,fighting,107,139,139,53,53,79,570
795,페로코체,Pheromosa,bug,fighting,71,137,37,137,37,151,570
796,전수목,Xurkitree,electric,,83,89,71,173,71,83,570
797,철화구야,Celesteela,steel,flying,97,101,103,107,101,61,570
798,종이신도,Kartana,grass,steel,59,181,131,59,31,109,570
799,악식킹,Guzzlord,dark,dragon,223,101,53,97,53,43,570
800,네크로즈마,Necrozma,psychic,,97,107,101,127,89,79,600
801,마기아나,Magearna,steel,fairy,80,95,115,130,115,65,600
802,마샤도,Marshadow,fighting,ghost,90,125,80,90,90,125,600
803,베베놈,Poipole,poison,,67,73,67,73,67,73,420
804,아고용,Naganadel,poison,dragon,73,73,73,127,73,121,540
805,차곡차곡,Stakataka,rock,steel,61,131,211,53,101,13,570
806,두파팡,Blacephalon,fire,ghost,53,127,53,151,79,107,570
807,제라오라,Zeraora,electric,,88,112,75,102,80,143,600
'''
def _load_base_stats(name_ko: str) -> Optional[dict[str, int]]:
    """pokemon.csv에서 종족값을 로드합니다."""
    #csv_path = POKEMON_CSV
    try:
        #with open(csv_path, encoding="utf-8-sig") as f:
        f=io.StringIO(THEPOKEMONCSV.strip())
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("이름_한글", "").strip() == name_ko:
                return {
                    "H": int(row["H"]),
                    "A": int(row["A"]),
                    "B": int(row["B"]),
                    "C": int(row["C"]),
                    "D": int(row["D"]),
                    "S": int(row["S"]),
                }
    except Exception as e:
        print(f"[CSV 오류] {e}", file=sys.stderr)
    return None


def _distribute_evs(stat_list: list[str]) -> dict[str, int]:
    """
    배틀트리 스타일 노력치 배분.
    첫 번째, 두 번째 스탯에 252씩, 세 번째 스탯에 4, 나머지 0.
    """
    evs: dict[str, int] = {}
    n = len(stat_list)
    if n == 0:
        return evs
    if n == 1:
        evs[stat_list[0]] = 252
    elif n == 2:
        evs[stat_list[0]] = 252
        evs[stat_list[1]] = 252
    else:
        evs[stat_list[0]] = 168
        evs[stat_list[1]] = 168
        evs[stat_list[2]] = 168
    return evs


# ══════════════════════════════════════════════════════════
#  시나리오 로더
# ══════════════════════════════════════════════════════════

def load_scenario(path: str) -> list[Pokemon]:
    """JSON 시나리오 파일에서 상대 팀(3마리)을 로드합니다."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    team: list[Pokemon] = []
    for entry in data:
        name   = entry["포켓몬"]
        types  = [PokemonType(t) for t in entry["타입"]]
        nature = entry["성격"]
        evs_raw= entry["노력치"]      # 리스트 형식
        item   = entry.get("지닌물건")
        ability= entry["특성"]
        move_names = entry["기술"]    # 최대 4개
        z_info = entry.get("Z기술")   # None or list
        mega   = entry.get("메가진화")# None or dict

        # 종족값 로드
        base_stats = _load_base_stats(name)
        if base_stats is None:
            print(f"[경고] {name} 종족값을 찾을 수 없습니다. 기본값 사용.", file=sys.stderr)
            base_stats = {"H":80,"A":80,"B":80,"C":80,"D":80,"S":80}

        # 노력치 변환
        evs = _distribute_evs(evs_raw)

        # 기술 변환
        moves = []
        for mn in move_names[:4]:
            m = _make_move(mn)
            if m is None:
                print(f"[경고] 기술 '{mn}' 을 DB에서 찾을 수 없습니다. 더미 기술 사용.", file=sys.stderr)
                m = Move(name=mn, type_=PokemonType.노말, category=MoveCategory.변화,
                         power=0, accuracy=None)
            moves.append(m)

        # Z기술 플래그 설정
        if z_info:
            for zi in z_info:
                base_name = zi["기반기술"]
                z_name    = zi["기술명"]
                for mv in moves:
                    if mv.name == base_name:
                        mv.is_z_move = True
                        mv.z_power   = get_z_move_power(mv)

        # 메가진화 정보
        mega_ability = None
        mega_types   = None
        if mega:
            mega_ability = mega.get("특성")
            if mega.get("타입"):
                mega_types = [PokemonType(t) for t in mega["타입"]]

        poke = Pokemon(
            name        = name,
            types       = types,
            nature      = nature,
            evs         = evs,
            base_stats  = base_stats,
            ability     = ability,
            moves       = moves,
            item        = item,
            mega_ability= mega_ability,
            mega_types  = mega_types,
        )
        team.append(poke)

    return team


# ══════════════════════════════════════════════════════════
#  플레이어 팀 정보 (고정 — my_problem.html 기준)
# ══════════════════════════════════════════════════════════

def _make_player_team() -> dict[str, Pokemon]:
    """
    문제에 주어진 6마리 포켓몬을 생성합니다.
    플레이어가 Team 명령으로 3마리를 선택하므로 전부 준비해둡니다.
    """
    def pk(name, types, nature, evs, base_stats, ability, item, move_names,
           mega_ability=None, mega_types=None):
        moves = [_make_move(mn) for mn in move_names]
        moves = [m for m in moves if m is not None]
        return Pokemon(
            name=name, types=[PokemonType(t) for t in types], nature=nature,
            evs=evs, base_stats=base_stats, ability=ability, item=item,
            moves=moves, mega_ability=mega_ability, mega_types=mega_types,
        )

    team = {}

    # 누리레느 (물/페어리 | 조심 | H252 C252 B4 | 누리레느Z | 급류)
    team["누리레느"] = pk(
        "누리레느", ["물","페어리"], "조심",
        {"H":252,"C":252,"B":4},
        {"H":95,"A":60,"B":65,"C":110,"D":130,"S":60},
        "급류", "누리레느Z",
        ["물거품아리아","문포스","아쿠아제트","냉동빔"],
    )

    # 카푸나비나 (에스퍼/페어리 | 조심 | C252 S252 H4 | 구애스카프 | 사이코메이커)
    team["카푸나비나"] = pk(
        "카푸나비나", ["에스퍼","페어리"], "조심",
        {"H":4,"C":252,"S":252},
        {"H":70,"A":55,"B":45,"C":95,"D":130,"S":85},
        "사이코메이커", "구애스카프",
        ["사이코키네시스","문포스","섀도볼","기합구슬"],
    )

    # 메타그로스 (강철/에스퍼 | 명랑 | A252 S252 H4 | 메타그로스나이트 | 클리어바디 → 단단한발톱)
    team["메타그로스"] = pk(
        "메타그로스", ["강철","에스퍼"], "명랑",
        {"H":4,"A":252,"S":252},
        {"H":80,"A":135,"B":130,"C":95,"D":90,"S":70},
        "클리어바디", "메타그로스나이트",
        ["아이언헤드","지진","사념의박치기","냉동펀치"],
        mega_ability="단단한발톱",
    )

    # 폴리곤2 (노말 | 차분 | H252 D252 B4 | 진화의휘석 | 다운로드)
    team["폴리곤2"] = pk(
        "폴리곤2", ["노말"], "차분",
        {"H":252,"B":4,"D":252},
        {"H":85,"A":80,"B":90,"C":105,"D":95,"S":60},
        "다운로드", "진화의휘석",
        ["방전","냉동빔","HP회복","맹독"],
    )

    # 한카리아스 (드래곤/땅 | 명랑 | A252 S252 D4 | 기합의띠 | 까칠한피부)
    team["한카리아스"] = pk(
        "한카리아스", ["드래곤","땅"], "명랑",
        {"A":252,"S":252,"D":4},
        {"H":108,"A":130,"B":95,"C":80,"D":85,"S":102},
        "까칠한피부", "기합의띠",
        ["역린","지진","칼춤","아이언헤드"],
    )

    # 윈디 (불꽃 | 고집 | A252 S252 H4 | 생명의구슬 | 위협)
    team["윈디"] = pk(
        "윈디", ["불꽃"], "고집",
        {"H":4,"A":252,"S":252},
        {"H":91,"A":110,"B":80,"C":100,"D":80,"S":95},
        "위협", "생명의구슬",
        ["신속","플레어드라이브","와일드볼트","인파이트"],
    )

    return team


# ══════════════════════════════════════════════════════════
#  NPC AI
# ══════════════════════════════════════════════════════════

def npc_choose_action(
    foe: Pokemon,
    foe_team: list[Pokemon],
    player: Pokemon,
    battle: BattleState,
    foe_mega_used: bool,
) -> Action:
    """
    NPC의 행동을 결정합니다.
    전략: 기절 시 다음 포켓몬 교체, 그 외 데미지 최대화 기술 선택.
    메가진화: 메가스톤을 가지고 있으면 첫 턴에 메가진화.
    """
    if foe.is_fainted:
        # 살아있는 다음 포켓몬 선택
        for p in foe_team:
            if not p.is_fainted and p is not foe:
                return Action(kind="change", pokemon=foe, is_player=False, switch_to=p)

    # 사용 가능한 기술 목록
    usable = [m for m in foe.moves if m.category != MoveCategory.변화 or True]
    if not usable:
        usable = foe.moves

    # 최대 예상 데미지 기술 선택
    best_move = usable[0]
    best_dmg  = -1
    for mv in usable:
        if mv.category == MoveCategory.변화:
            est = 0
        else:
            eff = get_type_effectiveness(mv.type_, player.types)
            if eff == 0:
                est = 0
            else:
                # 간이 추정 (랜덤 없이 base만)
                A_stat = foe.effective_stat("A" if mv.category == MoveCategory.물리 else "C")
                D_stat = player.max_stats["B" if mv.category == MoveCategory.물리 else "D"]
                power  = mv.z_power if mv.is_z_move else mv.power
                if power == 0:
                    power = 80
                est = int((int(2*foe.level/5+2) * A_stat * power / D_stat / 50 + 2) * float(eff))
        if est > best_dmg:
            best_dmg  = est
            best_move = mv

    # 메가진화 여부
    if (not foe_mega_used and not foe.is_mega
            and foe.mega_ability is not None
            and foe.item and "메가스톤" in foe.item):
        return Action(kind="mega", pokemon=foe, is_player=False, move=best_move)

    return Action(kind="move", pokemon=foe, is_player=False, move=best_move)


# ══════════════════════════════════════════════════════════
#  I/O 헬퍼
# ══════════════════════════════════════════════════════════

def send(msg: str) -> None:
    print(msg, flush=True)
    if 'You HP' not in msg:print('인터랙터: '+msg,file=sys.stderr)


def recv() -> str:
    line = sys.stdin.readline()
    print('나: '+line.rstrip(),file=sys.stderr)
    if not line:
        _wa("stdin이 예기치 않게 종료되었습니다.")
    return line.rstrip("\n")


def _wa(reason: str) -> None:
    print(f"[WA] {reason}", file=sys.stderr)
    sys.exit(1)


# ══════════════════════════════════════════════════════════
#  HP 상태 출력
# ══════════════════════════════════════════════════════════

def send_hp(player: Pokemon, foe: Pokemon) -> None:
    send(f"You HP {player.current_hp}/{player.max_stats['H']}, "
         f"Foe HP {foe.current_hp}/{foe.max_stats['H']}")


# ══════════════════════════════════════════════════════════
#  턴 진행 로직
# ══════════════════════════════════════════════════════════

class BattleSimulator:
    """배틀 전체 상태를 관리하는 시뮬레이터."""

    def __init__(self, foe_team: list[Pokemon], player_pool: dict[str, Pokemon]):
        self.foe_team   = foe_team
        self.player_pool= player_pool

        # 배틀 상태
        self.battle = BattleState()

        # 활성 포켓몬
        self.player_active: Optional[Pokemon] = None
        self.foe_active:    Optional[Pokemon] = None

        # 메가진화 배틀 내 1회 제한
        self.player_mega_used = False
        self.foe_mega_used    = False

        # 선택된 팀
        self.player_team: list[Pokemon] = []

        # 현재 배틀 번호 (50회)
        self.battle_num = 0

    # ── 팀 초기화 ─────────────────────────────────────────

    def setup_player_team(self, names: list[str]) -> None:
        """Team 명령으로 받은 3마리 이름으로 플레이어 팀 구성."""
        self.player_team = []
        for n in names:
            p = self.player_pool.get(n)
            if p is None:
                _wa(f"알 수 없는 포켓몬: {n}")
            self.player_team.append(p)

    def set_player_active(self, name: str) -> None:
        """Go 명령으로 선봉 설정."""
        for p in self.player_team:
            if p.name == name and not p.is_fainted:
                self.player_active = p
                return
        _wa(f"선봉 포켓몬 오류: {name}")

    def set_foe_active_first(self) -> Pokemon:
        """상대 첫 번째 포켓몬 출전."""
        for p in self.foe_team:
            if not p.is_fainted:
                self.foe_active = p
                return p
        _wa("상대 팀이 전부 기절 상태입니다.")

    def next_foe(self) -> Optional[Pokemon]:
        """다음 살아있는 상대 포켓몬."""
        for p in self.foe_team:
            if not p.is_fainted and p is not self.foe_active:
                return p
        return None

    # ── 쓰러뜨릴 때 발동 특성 ─────────────────────────────

    def _on_ko(self, killer: Pokemon, fallen: Pokemon) -> None:
        """상대를 쓰러뜨렸을 때 발동하는 특성 처리."""
        side = "Your" if killer is self.player_active else "Foes"
        ability = killer.ability
        killer.ko_count += 1

        # 자기과신 (Moxie): 쓰러뜨리면 A+1
        if ability == "자기과신":
            actual = killer.change_rank("A", +1)
            if actual: send(f"{side} pokemon rank A +{actual}")

        # 정의의마음 (Justice Heart): 강철/독 쓰러뜨리면 A+1
        if ability == "정의의마음":
            if any(t in fallen.types for t in [PokemonType.강철, PokemonType.독]):
                actual = killer.change_rank("A", +1)
                if actual: send(f"{side} pokemon rank A +{actual}")

    def _send_unlock_messages(self, pokemon: Pokemon) -> None:
        """
        플레이어 포켓몬이 필드에서 나갈 때,
        구애/앙코르/사슬묶기 등으로 잠긴 기술을 해제하고
        You can use X 메시지를 전송합니다.
        NPC 포켓몬에는 호출하지 않습니다.
        """
        CHOICE_ITEMS = {"구애띠", "구애안경", "구애스카프"}
        # 구애 고정 해제
        if pokemon.item in CHOICE_ITEMS and pokemon.locked_move:
            for mv in pokemon.moves:
                if mv.name != pokemon.locked_move:
                    send(f"You can use {mv.name}")
        # 앙코르 해제 (locked_move가 구애가 아닌 경우)
        elif pokemon.locked_move and pokemon.item not in CHOICE_ITEMS:
            for mv in pokemon.moves:
                if mv.name != pokemon.locked_move:
                    send(f"You can use {mv.name}")
        # 사슬묶기 해제
        if pokemon.disabled_move:
            send(f"You can use {pokemon.disabled_move}")

    # ── 출전 시 특성 발동 ─────────────────────────────────

    def _on_enter(self, entering: Pokemon, opponent: Pokemon) -> None:
        """포켓몬이 배틀 필드에 들어올 때 특성 발동."""
        events = apply_entry_ability(entering, opponent, self.battle)
        for ev in events:
            if ev.startswith("intimidate_") and "blocked" not in ev:
                # 위협 발동 → 상대 공격 1단계 하락 (already applied)
                pass
            elif ev.startswith("ability_"):
                pass  # 날씨/필드 발동은 이미 BattleState에 반영됨

    # ── 행동 파싱 ─────────────────────────────────────────

    def parse_player_action(self) -> Action:
        """
        학생 프로그램에서 행동을 읽습니다.
        Mega → 다음 줄에서 Use X 를 추가로 읽습니다.
        """
        line = recv()
        p    = self.player_active

        if line == "Mega":
            if self.player_mega_used:
                _wa("메가진화를 이미 사용했습니다.")
            if not p.mega_ability:
                _wa(f"{p.name}은(는) 메가진화 불가.")
            move_line = recv()
            if not move_line.startswith("Use "):
                _wa(f"Mega 직후 Use 명령이 필요합니다: {move_line!r}")
            move_name = move_line[4:].strip()
            mv = self._find_move(p, move_name)
            return Action(kind="mega", pokemon=p, is_player=True, move=mv)

        elif line.startswith("Use "):
            move_name = line[4:].strip()
            mv = self._find_move(p, move_name)
            return Action(kind="move", pokemon=p, is_player=True, move=mv)

        elif line.startswith("Change "):
            target_name = line[7:].strip()
            target = self._find_teammate(target_name)
            return Action(kind="change", pokemon=p, is_player=True, switch_to=target)

        else:
            _wa(f"알 수 없는 명령: {line!r}")

    def _find_move(self, pokemon: Pokemon, name: str) -> Move:
        """포켓몬의 기술 목록에서 이름으로 기술을 찾습니다."""
        # 앙코르/구애/역린: 이 기술만 사용 가능
        if pokemon.locked_move and name != pokemon.locked_move:
            _wa(f"{pokemon.name}은(는) '{pokemon.locked_move}'만 사용 가능합니다.")
        # 사슬묶기(Disable): 이 기술은 사용 불가
        if pokemon.disabled_move and name == pokemon.disabled_move:
            _wa(f"{pokemon.name}은(는) '{pokemon.disabled_move}'을(를) 사용할 수 없습니다(사슬묶기).")
        # 돌격조끼: 변화기 사용 불가
        # (기술 이름을 찾은 뒤 카테고리 체크는 아래에서 처리)
        for mv in pokemon.moves:
            if mv.name == name:
                # 돌격조끼: 변화기 사용 불가
                if pokemon.item == "돌격조끼" and mv.category == MoveCategory.변화:
                    _wa(f"{pokemon.name}은(는) 돌격조끼로 인해 변화기를 사용할 수 없습니다.")
                return mv
        # Z기술 이름으로도 검색
        for mv in pokemon.moves:
            if mv.is_z_move and name == f"Z{mv.name}":
                return mv
        _wa(f"{pokemon.name}의 기술 목록에 '{name}'이(가) 없습니다.")

    def _find_teammate(self, name: str) -> Pokemon:
        """살아있는 팀원을 이름으로 찾습니다."""
        for p in self.player_team:
            if p.name == name:
                if p.is_fainted:
                    _wa(f"{name}은(는) 이미 기절했습니다.")
                if p is self.player_active:
                    _wa(f"{name}은(는) 현재 배틀 중입니다.")
                return p
        _wa(f"팀에 {name}이(가) 없습니다.")

    # ── 교체 실행 ─────────────────────────────────────────

    def _execute_switch(self, action: Action) -> None:
        """교체 행동을 실행합니다."""
        leaving = action.pokemon
        incoming= action.switch_to if action.switch_to else None

        if action.is_player:
            if incoming is None:
                _wa("교체 대상이 없습니다.")
            # 교체로 나가면 구애/앙코르/사슬묶기 락 해제 → You can use X
            self._send_unlock_messages(leaving)
            apply_switch_out_ability(leaving)
            leaving.reset_battle_volatile()
            self.player_active = incoming
            self._on_enter(incoming, self.foe_active)
            send(f"You sent out {incoming.name}")
        else:
            if incoming is None:
                incoming = action.switch_to
            if incoming:
                apply_switch_out_ability(leaving)
                leaving.reset_battle_volatile()
                self.foe_active = incoming
                self._on_enter(incoming, self.player_active)
                send(f"Foe sent out {incoming.name}")

    # ── 기술 실행 ─────────────────────────────────────────

    def _execute_move(
        self,
        attacker: Pokemon,
        defender: Pokemon,
        move:     Move,
        is_player_turn: bool,
        used_mega_this_action: bool = False,
    ) -> None:
        """
        기술 사용 한 번을 처리합니다.
        상태이상 체크 → 기술 발동 → 데미지 → 부가효과 → HP 전송.
        """
        prefix = "You" if is_player_turn else "Foe"

        # ── 2턴 기술: 1턴차(충전) 처리 ─────────────────────
        if move.name in TWO_TURN_MOVES and attacker.charge_move is None:
            skip_charge = (
                move.name in ("솔라빔", "솔라블레이드")
                and self.battle.weather == Weather.SUNNY
            )
            if not skip_charge:
                send(f"{prefix} used {move.name}")
                attacker.charge_move = move.name
                attacker.charge_invulnerable = move.name in INVULNERABLE_CHARGE_MOVES
                if move.name == "로켓박치기":
                    actual = attacker.change_rank("B", +1)
                    side = "Your" if is_player_turn else "Foes"
                    if actual:
                        send(f"{side} pokemon rank B +{actual}")
                send_hp(self.player_active, self.foe_active)
                return

        # ── 2턴 기술: 2턴차 진입 시 charge 초기화 ──────────
        if attacker.charge_move == move.name:
            attacker.charge_move = None
            attacker.charge_invulnerable = False

        # ── 풍선: 땅 기술 무효 (터지기 전까지) ─────────────
        if (defender.item == "풍선"
                and move.type_ == PokemonType.땅
                and move.category != MoveCategory.변화):
            send(f"{prefix} used {move.name}")
            send("Failed")
            send_hp(self.player_active, self.foe_active)
            return

        # ── 무효화 특성 체크 ────────────────────────────────
        is_mold_breaker = attacker.ability in ("틀깨기", "터보블레이즈", "테라볼티지")
        if not is_mold_breaker and move.category != MoveCategory.변화:
            d_ab = defender.ability
            mtype = move.type_
            absorbed = False
            if d_ab == "피뢰침" and mtype == PokemonType.전기:
                send(f"{prefix} used {move.name}")
                actual = defender.change_rank("C", +1)
                s2 = "Foes" if is_player_turn else "Your"
                if actual: send(f"{s2} pokemon rank C +{actual}")
                send_hp(self.player_active, self.foe_active)
                absorbed = True
            elif d_ab == "발광" and mtype == PokemonType.불꽃:
                send(f"{prefix} used {move.name}")
                send("Failed")
                send_hp(self.player_active, self.foe_active)
                absorbed = True
            elif d_ab == "초식" and mtype == PokemonType.풀:
                send(f"{prefix} used {move.name}")
                actual = defender.change_rank("A", +1)
                s2 = "Foes" if is_player_turn else "Your"
                if actual: send(f"{s2} pokemon rank A +{actual}")
                send_hp(self.player_active, self.foe_active)
                absorbed = True
            elif d_ab == "부유" and mtype == PokemonType.땅:
                send(f"{prefix} used {move.name}")
                send("Failed")
                send_hp(self.player_active, self.foe_active)
                absorbed = True
            elif d_ab == "축전" and mtype == PokemonType.전기:
                send(f"{prefix} used {move.name}")
                defender.heal(max(1, defender.max_stats["H"] // 4))
                send_hp(self.player_active, self.foe_active)
                absorbed = True
            if absorbed:
                return

        # ── 충전 중 무적 상태 → 빗나감 ──────────────────────
        if defender.charge_invulnerable:
            send(f"{prefix} used {move.name}")
            send("Missed")
            send_hp(self.player_active, self.foe_active)
            return

        # 대타출동 방어 확인
        if defender.protect_active and move.priority >= 0:
            send(f"{prefix} used {move.name}")
            send("Failed")
            send_hp(
                self.player_active if is_player_turn else defender,
                self.foe_active    if is_player_turn else attacker,
            )
            return

        # 상태이상 체크 (기술 사용 전)
        status_result = check_status_before_move(attacker)
        if not status_result["can_move"]:
            ev = status_result["event"]
            if ev == "sleep":
                send(f"{prefix} used {move.name}")
                send("Failed")
            elif ev == "sleep_wake":
                send(f"{prefix} used {move.name}")
                send("Failed")
                send(f"{'Your' if is_player_turn else 'Foes'} pokemon heal SLP")
            elif ev == "frozen":
                send(f"{prefix} used {move.name}")
                send("Failed")
            elif ev == "par_full":
                send(f"{prefix} used {move.name}")
                send("Failed")
            elif ev == "confusion_self_hit":
                send(f"{prefix} used {move.name}")
                send("Failed")
                send_hp(
                    self.player_active if is_player_turn else defender,
                    self.foe_active    if is_player_turn else attacker,
                )
            return
        else:
            # 해동 처리
            if status_result["event"] == "thaw":
                send(f"{'Your' if is_player_turn else 'Foes'} pokemon heal FRZ")

        # 기술 선언
        send(f"{prefix} used {move.name}")

        # ── 구애 아이템 기술 고정 처리 ─────────────────────
        CHOICE_ITEMS = {"구애띠", "구애안경", "구애스카프"}
        if attacker.item in CHOICE_ITEMS and not attacker.locked_move:
            # 이 기술로 고정 → 나머지 기술에 You cant use X
            attacker.locked_move = move.name
            if is_player_turn:
                for mv in attacker.moves:
                    if mv.name != move.name:
                        send(f"You cant use {mv.name}")

        # 기술 록 업데이트 (last_used_move)
        attacker.last_used_move = move.name

        # 변화기 처리
        if move.category == MoveCategory.변화:
            events = apply_stat_move(attacker, defender, move, self.battle)
            self._send_stat_events(events, is_player_turn)
            send_hp(self.player_active, self.foe_active)
            return

        # ── 습기(Damp): 자폭/대폭발 기술 무효화 ─────────────
        SELFDESTRUCT_MOVES = {"자폭", "대폭발", "최후의수단", "메모리지우기"}
        if move.name in SELFDESTRUCT_MOVES:
            for poke in [self.player_active, self.foe_active]:
                if poke and poke.ability == "습기":
                    send(f"{prefix} used {move.name}")
                    send("Failed")
                    send_hp(self.player_active, self.foe_active)
                    return

        # ── 충전 중 무적 상태 대상 → 빗나감 ──────────────────
        if defender.charge_invulnerable:
            send("Missed")
            send_hp(self.player_active, self.foe_active)
            return

        # 명중 판정
        if move.accuracy is not None:
            acc_num, acc_den = attacker.acc_eva_multiplier("명")
            eva_num, eva_den = defender.acc_eva_multiplier("회")
            hit_chance = move.accuracy * acc_num / acc_den * eva_den / eva_num
            # 광각렌즈: 명중률 ×1.1
            if attacker.item == "광각렌즈":
                hit_chance *= 1.1
            # 초점렌즈/포커스렌즈: 명중률 +10%
            if attacker.item in ("초점렌즈", "포커스렌즈"):
                hit_chance += 10
            # 무사태평향로: 방어자 아이템, 공격자 명중률 -10%
            if defender.item == "무사태평향로":
                hit_chance -= 10
            hit_chance = min(100.0, max(1.0, hit_chance))
            if random.random() * 100 > hit_chance:
                send("Missed")
                send_hp(self.player_active, self.foe_active)
                return

        # 다단히트 횟수 결정
        if move.effect.multi_hit:
            lo, hi = move.effect.multi_hit
            hit_count = random.choices(
                range(lo, hi+1),
                weights=[35,35,15,15] if hi-lo==3 else None
            )[0]
        else:
            hit_count = 1

        total_damage = 0
        for _ in range(hit_count):
            result = calculate_damage(attacker, defender, move, self.battle)
            dmg    = result["damage"]
            # 급소는 HP 변화로만 확인 (별도 메시지 없음)

            # 데미지 적용
            if defender.substitute_hp > 0 and not move.is_z_move:
                defender.substitute_hp -= dmg
                if defender.substitute_hp <= 0:
                    defender.substitute_hp = 0
                    # 대타 파괴
            else:
                defender.take_damage(dmg)

            total_damage += dmg

        # HP 전송
        send_hp(self.player_active, self.foe_active)

        # 피격 플래그 (애널라이즈용)
        if total_damage > 0:
            defender.been_attacked = True

        # 타입 상성 무효 → (데미지 0이지만 HP 전송은 함)
        if total_damage == 0 and move.category != MoveCategory.변화:
            return

        # 부가효과
        events = apply_move_secondary_effect(
            attacker, defender, move, total_damage, self.battle
        )
        self._send_stat_events(events, is_player_turn)

        # 접촉 특성
        contact_events = apply_contact_ability(attacker, defender, move)
        self._send_stat_events(contact_events, is_player_turn)

        # 생명의 구슬 반동
        if attacker.item == "생명의구슬" and total_damage > 0:
            lb_dmg = max(1, attacker.max_stats["H"] // 10)
            attacker.take_damage(lb_dmg)
            if attacker.current_hp == 0:
                send_hp(self.player_active, self.foe_active)

        # ── 약점보험 (Weakness Policy): 효과 굉장 → A+C+2 ──
        _teff = get_type_effectiveness(move.type_, defender.types)
        if (defender.item == "약점보험"
                and _teff > Fraction(1)
                and not defender.is_fainted
                and total_damage > 0):
            defender.item = None
            actual_a = defender.change_rank("A", +2)
            actual_c = defender.change_rank("C", +2)
            side2 = "Foes" if is_player_turn else "Your"
            if actual_a: send(f"{side2} pokemon rank A +{actual_a}")
            if actual_c: send(f"{side2} pokemon rank C +{actual_c}")

        # ── 불굴의마음 (Justified): 악 기술 맞으면 A+1 ──────
        if (move.type_ == PokemonType.악
                and defender.ability == "불굴의마음"
                and not defender.is_fainted
                and total_damage > 0):
            actual = defender.change_rank("A", +1)
            side2 = "Foes" if is_player_turn else "Your"
            if actual: send(f"{side2} pokemon rank A +{actual}")

        # ── 정의의마음 (Justice Heart): 강철/독 쓰러뜨리면 A+1
        # 자기과신 (Moxie): 쓰러뜨리면 A+1 → 기절 처리 후 _on_ko에서 처리

        # ── 하양허브 (White Herb): 랭크 하락된 스탯 한 번 복구 ─
        if attacker.item == "하양허브":
            restored = any(attacker.rank[s] < 0 for s in ["A","B","C","D","S"])
            if restored:
                for s in ["A","B","C","D","S"]:
                    if attacker.rank[s] < 0:
                        attacker.rank[s] = 0
                attacker.item = None

    def _send_stat_events(self, events: list[str], is_player: bool) -> None:
        """이벤트 목록을 프로토콜 메시지로 변환하여 전송합니다."""
        for ev in events:
            if ev.startswith("rank_"):
                parts = ev.split("_")
                poke_name = parts[1]
                stat      = parts[2]
                change    = parts[3]
                if poke_name == self.player_active.name:
                    side = "Your"
                else:
                    side = "Foes"
                send(f"{side} pokemon rank {stat} {change}")

            elif ev.startswith("status_"):
                cond = ev[7:]
                side = "Foes" if is_player else "Your"
                send(f"{side} pokemon status {cond}")

            elif ev.startswith("volatile_"):
                cond = ev[9:]
                if cond == "FLI":
                    side = "Foes" if is_player else "Your"
                    send(f"{side} pokemon status FLI")

            elif ev.startswith("encore_"):
                # encore_기술명: 상대에게 앙코르 적용 → 플레이어가 걸면 상대에게
                # 여기서는 플레이어가 걸었을 때 상대 포켓몬의 메시지는 없음
                # 플레이어가 앙코르에 걸렸으면: is_player=False(NPC가 건 것)
                if not is_player:
                    # 플레이어가 앙코르에 걸림 → 고정 기술 외 You cant use X
                    locked = self.player_active.locked_move
                    if locked:
                        for mv in self.player_active.moves:
                            if mv.name != locked:
                                send(f"You cant use {mv.name}")

            elif ev.startswith("cursed_body_disable_"):
                # 저주받은바디로 플레이어 기술 사슬묶기
                disabled = ev[len("cursed_body_disable_"):]
                # 사슬묶기 당한 것이 플레이어 포켓몬인지 확인
                if self.player_active.disabled_move == disabled:
                    send(f"You cant use {disabled}")

            elif ev.startswith("recoil_") or ev.startswith("drain_"):
                pass

            elif ev == "flinch":
                side = "Foes" if is_player else "Your"
                send(f"{side} pokemon status FLI")

            elif ev in ("mist_field_blocked_status",):
                pass

            elif ev.startswith("liquid_ooze") or ev.startswith("natural_cure") \
                    or ev.startswith("regenerator"):
                pass

    # ── 턴 종료 처리 ──────────────────────────────────────

    def _end_of_turn(self) -> None:
        """턴 종료: 지속 데미지, 날씨 틱, 풀죽음 리셋."""
        for poke, is_player in [
            (self.player_active, True),
            (self.foe_active,    False),
        ]:
            if poke is None or poke.is_fainted:
                continue
            events = apply_end_of_turn_damage(poke, self.battle)
            side = "Your" if is_player else "Foes"
            for ev in events:
                if "sandstorm" in ev or "hail" in ev:
                    weather = "sandstorm" if "sandstorm" in ev else "hail"
                    send(f"{side} pokemon damaged by environment {weather}")
                elif "psn_damage" in ev:
                    send(f"{side} pokemon damaged by status PSN")
                elif "tox_damage" in ev:
                    send(f"{side} pokemon damaged by status TOX")
                elif "brn_damage" in ev:
                    send(f"{side} pokemon damaged by status BRN")
                elif "bind_damage" in ev:
                    send(f"{side} pokemon damaged by status BND")
                elif "heal" in ev or "leftovers" in ev:
                    pass  # HP 자동 갱신은 Turn end 전에 처리
            if not poke.is_fainted:
                send_hp(self.player_active, self.foe_active)

        # 가속 특성 (턴 종료 시)
        for poke, _ in [(self.player_active, True), (self.foe_active, False)]:
            if poke and not poke.is_fainted and poke.ability == "가속":
                actual = poke.change_rank("S", +1)
                side = "Your" if poke is self.player_active else "Foes"
                if actual:
                    send(f"{side} pokemon rank S +{actual}")

        # 날씨 틱
        result = self.battle.tick_all()
        for room in result["rooms_ended"]:
            send(f"Environment {room.value} end")
        if result["field_ended"]:
            pass  # 필드 종료 메시지
        if result["weather_ended"]:
            pass  # 날씨 종료

        # 풀죽음 리셋
        for poke in [self.player_active, self.foe_active]:
            if poke:
                poke.cure_volatile(VolatileStatus.FLI)
        # 방어 리셋 + 피격 플래그 리셋
        for poke in [self.player_active, self.foe_active]:
            if poke:
                poke.protect_active = False
                poke.been_attacked = False
                poke.stat_dropped_this_turn = False
        # 사슬묶기(Disable) 카운터 감소
        for poke in [self.player_active, self.foe_active]:
            if poke and poke.disable_counter > 0:
                poke.disable_counter -= 1
                if poke.disable_counter <= 0:
                    if poke is self.player_active and poke.disabled_move:
                        send(f"You can use {poke.disabled_move}")
                    poke.disabled_move = None
        # 앙코르 카운터 감소
        for poke in [self.player_active, self.foe_active]:
            if poke and poke.encore_counter > 0:
                poke.encore_counter -= 1
                if poke.encore_counter <= 0:
                    if poke is self.player_active and poke.locked_move:
                        # 앙코르 해제: 고정된 기술 외 기술들을 다시 사용 가능
                        for mv in poke.moves:
                            if mv.name != poke.locked_move:
                                send(f"You can use {mv.name}")
                    poke.locked_move = None

    # ── 메인 배틀 루프 ────────────────────────────────────
    def run_battle(self) -> bool:
        """
        1회 배틀을 진행합니다.
        Return True = Victory, False = Defeat.
        """
        self.battle.reset()
        self.player_mega_used = False
        self.foe_mega_used    = False

        # 포켓몬 상태 리셋
        for p in self.player_team + self.foe_team:
            p.reset_battle_volatile()
            p.is_fainted    = False
            p.current_hp    = p.max_stats["H"]
            p.status        = None
            p.toxic_counter = 0
            p.sleep_counter = 0
            p.z_used        = False
            p.slow_start_counter = 0
            p.ko_count      = 0

        # ── 초기 출전 ──────────────────────────────────────────
        send(f"You sent out {self.player_active.name}")
        foe_first = self.set_foe_active_first()
        # 출전 특성 (위협, 다운로드, 필드 발동 등)
        self._on_enter(self.player_active, foe_first)
        self._on_enter(foe_first, self.player_active)
        send(f"Foe sent out {foe_first.name}")

        # 필드 발동 메시지 (사이코메이커 등)
        for poke in [self.player_active, self.foe_active]:
            field_map = {
                "사이코메이커": "PT", "미스트메이커": "MT",
                "일렉트릭메이커": "ET", "그래스메이커": "GT",
            }
            if poke.ability in field_map:
                send(f"Environment {field_map[poke.ability]} start")

        send("Turn end")

        # ── 턴 루프 ────────────────────────────────────────────
        while True:

            # ── 1. 플레이어 행동 입력 ──────────────────────────
            player_action = self.parse_player_action()

            # ── 2. NPC 행동 결정 & 공개 ───────────────────────
            # NPC는 플레이어 행동에 영향받지 않으므로 먼저 결정
            foe_action = npc_choose_action(
                self.foe_active, self.foe_team,
                self.player_active, self.battle,
                self.foe_mega_used,
            )
            # 명세: 플레이어 행동 출력 직후 NPC 행동이 입력으로 들어옴
            if foe_action.kind == "mega":
                send("Mega")
                send(f"Use {foe_action.move.name}")
            elif foe_action.kind == "change":
                send(f"Change {foe_action.switch_to.name}")
            else:
                send(f"Use {foe_action.move.name}")

            # ── 3. 메가진화 처리 (행동 순서보다 먼저, 턴 시작 시) ─
            if player_action.kind == "mega":
                apply_mega_evolution(self.player_active, self.player_mega_used)
                self.player_mega_used = True
                send("You used Mega")
                player_action = Action(
                    kind="move", pokemon=self.player_active,
                    is_player=True, move=player_action.move,
                )
            if foe_action.kind == "mega":
                apply_mega_evolution(self.foe_active, self.foe_mega_used)
                self.foe_mega_used = True
                send("Foe used Mega")
                foe_action = Action(
                    kind="move", pokemon=self.foe_active,
                    is_player=False, move=foe_action.move,
                )

            # ── 4. 행동 순서 결정 ─────────────────────────────
            ordered = determine_turn_order(player_action, foe_action, self.battle)

            # ── 5. 순서대로 행동 실행 ─────────────────────────
            # skip_*: 기절 → 교체 출전한 측은 이 턴 남은 행동 취소
            skip_player = False
            skip_foe    = False

            for action in ordered:
                is_player = action.is_player

                if is_player and skip_player:
                    continue
                if not is_player and skip_foe:
                    continue

                # 행동 주체를 매번 최신 값으로 갱신 (교체로 바뀔 수 있음)
                actor  = self.player_active if is_player else self.foe_active
                target = self.foe_active    if is_player else self.player_active

                if actor.is_fainted:
                    continue

                # ── 교체 행동 ────────────────────────────────
                if action.kind == "change":
                    self._execute_switch(action)
                    if is_player:
                        self._on_enter(self.player_active, self.foe_active)
                    else:
                        self._on_enter(self.foe_active, self.player_active)

                # ── 기술 행동 ────────────────────────────────
                elif action.kind == "move":
                    mv = action.move
                    # 풀죽음 체크
                    if VolatileStatus.FLI in actor.volatile_statuses:
                        send(f"{'You' if is_player else 'Foe'} used {mv.name}")
                        send("Failed")
                        send_hp(self.player_active, self.foe_active)
                        continue

                    self._execute_move(actor, target, mv, is_player)

                # ── 방어 대상(target) 기절 처리 ──────────────
                # target 변수는 action 시작 시 할당됐으므로 교체 후에도 유효
                if target.is_fainted:
                    if is_player:
                        send("Foes pokemon fainted")
                        self._on_ko(actor, target)  # 자기과신/정의의마음
                        next_foe = self.next_foe()
                        if next_foe is None:
                            send("Victory")
                            return True
                        self.foe_active = next_foe
                        self._on_enter(next_foe, self.player_active)
                        send(f"Foe sent out {next_foe.name}")
                        skip_foe = True
                    else:
                        send("Your pokemon fainted")
                        alive = [p for p in self.player_team if not p.is_fainted]
                        if not alive:
                            send("Defeat")
                            return False
                        self._send_unlock_messages(actor)   # 락 해제 메시지
                        go_line = recv()
                        if not go_line.startswith("Go "):
                            _wa(f"기절 후 Go 명령 필요: {go_line!r}")
                        next_name = go_line[3:].strip()
                        found = next(
                            (p for p in self.player_team
                            if p.name == next_name and not p.is_fainted),
                            None,
                        )
                        if found is None:
                            _wa(f"교체 불가 포켓몬: {next_name}")
                        apply_switch_out_ability(actor)   # 기절 포켓몬 switch-out 특성
                        self.player_active = found
                        self._on_enter(found, self.foe_active)
                        send(f"You sent out {found.name}")
                        skip_player = True

                # ── 행동 주체(actor) 기절 처리 (반동 등) ──────
                if actor.is_fainted:
                    if is_player:
                        send("Your pokemon fainted")
                        alive = [p for p in self.player_team if not p.is_fainted]
                        if not alive:
                            send("Defeat")
                            return False
                        self._send_unlock_messages(actor)   # 락 해제 메시지
                        go_line = recv()
                        if not go_line.startswith("Go "):
                            _wa(f"기절 후 Go 명령 필요: {go_line!r}")
                        next_name = go_line[3:].strip()
                        found = next(
                            (p for p in self.player_team
                            if p.name == next_name and not p.is_fainted),
                            None,
                        )
                        if found is None:
                            _wa(f"교체 불가: {next_name}")
                        self.player_active = found
                        self._on_enter(found, self.foe_active)
                        send(f"You sent out {found.name}")
                        skip_player = True
                    else:
                        send("Foes pokemon fainted")
                        next_foe = self.next_foe()
                        if next_foe is None:
                            send("Victory")
                            return True
                        self.foe_active = next_foe
                        self._on_enter(next_foe, self.player_active)
                        send(f"Foe sent out {next_foe.name}")
                        skip_foe = True

            # ── 6. 턴 종료 처리 ───────────────────────────────
            self._end_of_turn()

            # 턴 종료 데미지로 기절한 경우 처리
            if self.player_active.is_fainted:
                send("Your pokemon fainted")
                alive = [p for p in self.player_team if not p.is_fainted]
                if not alive:
                    send("Defeat")
                    return False
                self._send_unlock_messages(self.player_active)   # 락 해제 메시지
                go_line = recv()
                if not go_line.startswith("Go "):
                    _wa(f"기절 후 Go 명령 필요: {go_line!r}")
                next_name = go_line[3:].strip()
                found = next(
                    (p for p in self.player_team
                    if p.name == next_name and not p.is_fainted),
                    None,
                )
                if found is None:
                    _wa(f"교체 불가: {next_name}")
                self.player_active = found
                self._on_enter(found, self.foe_active)
                send(f"You sent out {found.name}")

            if self.foe_active.is_fainted:
                next_foe = self.next_foe()
                if next_foe is None:
                    send("Victory")
                    return True
                self.foe_active = next_foe
                self._on_enter(next_foe, self.player_active)
                send(f"Foe sent out {next_foe.name}")

            send("Turn end")

# ══════════════════════════════════════════════════════════
#  메인 진입점
# ══════════════════════════════════════════════════════════

def main() -> None:
    
    if len(sys.argv) < 2:
        print("사용법: interactor.py <시나리오_json_경로>", file=sys.stderr)
        sys.exit(1)
    scenario_path = sys.argv[1]
    print("------ 배틀 기록 ------",file=sys.stderr)
    # 시나리오 로드 (상대 팀 3마리)
    foe_team = load_scenario(scenario_path)

    # 플레이어 풀 (6마리)
    player_pool = _make_player_team()

    sim = BattleSimulator(foe_team, player_pool)

    # ── 초기화 단계 ──────────────────────────────────────
    # Team A B C
    team_line = recv()
    if not team_line.startswith("Team "):
        _wa(f"Team 명령이 필요합니다: {team_line!r}")
    team_names = team_line[5:].strip().split()
    if len(team_names) != 3:
        _wa(f"팀은 정확히 3마리여야 합니다: {team_names}")
    sim.setup_player_team(team_names)

    # Go P
    go_line = recv()
    if not go_line.startswith("Go "):
        _wa(f"Go 명령이 필요합니다: {go_line!r}")
    first_name = go_line[3:].strip()
    sim.set_player_active(first_name)

    # ── 배틀 시작 ─────────────────────────────────────────
    result = sim.run_battle()

    if result:
        sys.exit(0)   # Victory → 정답
    else:
        print('플레이어는 눈앞이 깜깜해졌다...',file=sys.stderr)
        sys.exit(1)   # Defeat → 오답


if __name__ == "__main__":
    main()