# Rental Raw Data Audit V1

## Overview
- **Source File**: `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv`
- **SHA256**: `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d`
- **Raw Rows**: 573,001
- **Loaded (TOTAL_PROPERTIES==1, Residential, Unit/Villa, valid bounds)**: 384,161
- **Filtered**: 188,840

## Contracts by Version
| Version | Count |
|---------|-------|
| New | 150,825 |
| Renewed | 233,336 |

## Contracts by Property Type
| Property Type | Count |
|---------------|-------|
| Unit | 350,775 |
| Villa | 33,386 |

## Contracts by Property Sub-Type (Top 15)
| Sub-Type | Count |
|----------|-------|
| Flat | 343,731 |
| Villa | 31,252 |
| Studio | 3,838 |
| Labor Camps | 2,930 |
| Complex Villas | 2,141 |
| (empty) | 96 |
| Staff Accommodation | 64 |
| Building | 48 |
| Mezzanine | 21 |
| Arabian House | 18 |
| Penthouse | 13 |
| Villa addendum | 6 |
| Portacabin | 1 |
| Hotel | 1 |
| Store | 1 |

## Area Coverage (Top 20)
| DLD Rental Area | Contracts |
|-----------------|-----------|
| Al Barsha South Fourth | 19,363 |
| Al Warsan First | 17,023 |
| Jabal Ali First | 16,876 |
| Al Khairan First | 12,817 |
| Business Bay | 12,565 |
| Burj Khalifa | 11,943 |
| Marsa Dubai | 10,697 |
| Nadd Hessa | 10,543 |
| Al Nahda Second | 8,210 |
| Al Barshaa South Third | 8,143 |
| Al Barsha First | 7,933 |
| Al Karama | 7,872 |
| Me'Aisem First | 7,613 |
| Wadi Al Safa 5 | 7,157 |
| Muhaisanah Fourth | 7,090 |
| Al Nahda First | 6,817 |
| Al Murqabat | 6,610 |
| Al Merkadh | 6,403 |
| Mirdif | 6,189 |
| Al Warqa First | 6,185 |

**Total unique DLD rental areas**: 181

## Project Coverage
- **Unique projects with rental data**: 1,623
- **Contracts with missing/empty project_key**: 244,330 (63.6%)

### Top 20 Projects
| Project (normalized) | Contracts |
|----------------------|-----------|
| remraam | 1,486 |
| remraam al ramth | 1,486 |
| remraam al ramth 2 | 1,486 |
| sky courts | 938 |
| lakeside | 913 |
| international city emarati | 911 |
| creek beach rosewater | 871 |
| creek beach savanna cedar mangrove | 871 |
| creek beach canopy moor | 871 |
| creek beach orchid | 871 |
| creek beach vida residences | 871 |
| creek beach sunset | 871 |
| creek beach breeze | 871 |
| creek beach bayshore | 871 |
| creek beach lotus | 870 |
| creek beach surf | 870 |
| creek beach summer | 870 |
| creek beach grove | 869 |
| ritaj | 672 |
| il primo | 639 |

## Bedroom Distribution
| Bedrooms | Contracts |
|----------|-----------|
| 0 (Studio) | 3,903 |
| 1 | 341 |
| 2 | 1,909 |
| 3 | 12,322 |
| 4 | 6,602 |
| 5 | 1,614 |
| 6 | 316 |
| 7 | 24 |
| 8 | 3 |

**Note**: 96.8% of raw rows had empty ROOMS field; bedrooms inferred from PROP_SUB_TYPE_EN where possible.

## Date Range
- **Registration Date Range**: 2026-01-01 to 2026-08-09

## Size Statistics (sqft)
| Statistic | Value |
|-----------|-------|
| Min | 108 |
| Max | 81,849 |
| Median | 904 |
| Mean | 1,166 |

## Annual Rent Statistics (AED)
| Statistic | Value |
|-----------|-------|
| Min | 10,000 |
| Max | 5,000,000 |
| Median | 66,500 |
| Mean | 92,644 |

## PSF Statistics (AED/sqft/year)
| Statistic | Value |
|-----------|-------|
| Min | 20 |
| Max | 4,831 |
| Median | 76 |
| Mean | 88 |

## TOTAL_PROPERTIES Breakdown
| TOTAL_PROPERTIES | Count |
|------------------|-------|
| 1 | 384,161 |

## Property Class Distribution
| Property Class | Count |
|----------------|-------|
| residential | 384,161 |

## Key Observations
1. **High missing project rate**: 63.6% of contracts have empty PROJECT_EN, limiting exact-project matching (R1/R2).
2. **Bedroom sparsity**: Only 3,903 contracts have bedrooms > 0 from ROOMS field; most inferred from PROP_SUB_TYPE_EN (Studio=0, Flat≈1-2, Villa≈3-4).
3. **Date range limited**: All contracts are from 2026 (Jan-Aug), making true temporal holdout challenging.
4. **Area coverage**: 181 DLD rental areas, but MASTER areas map to only a subset.
5. **PSF median ~76 AED/sqft/year**: Validates sqm→sqft conversion correctness.
6. **No multi-property contracts**: All loaded contracts have TOTAL_PROPERTIES==1 (filtered).

## Validation Bounds Applied
- MIN_ANNUAL_RENT: 10,000 AED
- MAX_ANNUAL_RENT: 5,000,000 AED
- MIN_ACTUAL_AREA_SQFT: 100
- MAX_ACTUAL_AREA_SQFT: 215,000
- MIN_PSF: 20
- MAX_PSF: 5,000
- RESIDENTIAL_USAGE: "Residential" only
- ALLOWED_PROP_TYPES: "Unit", "Villa" only
