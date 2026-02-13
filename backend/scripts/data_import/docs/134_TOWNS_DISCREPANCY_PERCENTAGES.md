# Discrepancy % and import stats for all 134 towns (134 flow)

**Source:** Log `full_134_import_20260206_100508.log` (full 134-town run).
**Columns:**
- **Inserted** = number of properties inserted in this run
- **Updated** = number updated
- **Cleaned Excel count** = records in cleaned Excel (when present in log)
- **Geodatabase total** = total parcels in geodatabase Excel (with geometry)
- **Final DB count** = properties for this town in DB after run
- **Discrepancy (n)** = Geodatabase total − Final DB count
- **Discrepancy %** = Discrepancy (n) / Geodatabase total; >10% = significant.
- **Status** = success / skipped / failed / not in log

| # | Town | Inserted | Updated | Cleaned Excel count | Geodatabase total | Final DB count | Discrepancy (n) | Discrepancy % | Status |
|---|------|----------|---------|---------------------|-------------------|----------------|-----------------|---------------|--------|
| 1 | Waterbury | 0 | 27,762 | — | 29,305 | 27,762 | 1,543 | 5.3% | success |
| 2 | NEW HAVEN | 0 | 26,216 | — | 26,858 | 26,216 | 642 | 2.4% | success |
| 3 | West hartford | 0 | 21,859 | — | 22,609 | 21,859 | 750 | 3.3% | success |
| 4 | Bristol | 0 | 19,850 | — | 21,975 | 19,850 | 2,125 | 9.7% | success |
| 5 | Fairfield | 0 | 19,716 | — | 19,620 | 19,716 | -96 | -0.5% | success |
| 6 | Greenwich | 0 | 14 | — | 19,364 | 14 | 19,350 | 99.9% | success |
| 7 | Milford | 0 | 18,915 | — | 19,408 | 18,915 | 493 | 2.5% | success |
| 8 | Southington | 0 | 18,276 | — | 18,482 | 18,276 | 206 | 1.1% | success |
| 9 | Berlin | 0 | 8,669 | — | 18,036 | 8,669 | 9,367 | 51.9% | success |
| 10 | West Haven | 0 | 11,947 | — | 16,942 | 11,947 | 4,995 | 29.5% | success |
| 11 | Stratford | 0 | 17,427 | — | 17,876 | 17,427 | 449 | 2.5% | success |
| 12 | Hamden | 0 | 16,627 | — | 16,749 | 16,627 | 122 | 0.7% | success |
| 13 | Wallingford | 0 | 16,369 | — | 16,758 | 16,369 | 389 | 2.3% | success |
| 14 | MERIDEN | 1 | 15,643 | — | 16,506 | 15,644 | 862 | 5.2% | success |
| 15 | New britain | 0 | 15,523 | — | 15,737 | 15,523 | 214 | 1.4% | success |
| 16 | Glastonbury | 0 | 13,359 | — | 15,315 | 13,359 | 1,956 | 12.8% | success |
| 17 | East hartford | 0 | 14,295 | — | 14,284 | 14,295 | -11 | -0.1% | success |
| 18 | Norwich | 0 | 13,232 | — | 14,132 | 13,232 | 900 | 6.4% | success |
| 19 | New Milford | 0 | 12,861 | — | 13,713 | 12,861 | 852 | 6.2% | success |
| 20 | Branford | 0 | 13,164 | — | 13,541 | 13,164 | 377 | 2.8% | success |
| 21 | Shelton | 0 | 12,475 | — | 13,297 | 12,475 | 822 | 6.2% | success |
| 22 | Groton | 0 | 9,478 | — | 13,062 | 9,478 | 3,584 | 27.4% | success |
| 23 | Newington | 0 | 12,452 | — | 12,532 | 12,452 | 80 | 0.6% | success |
| 24 | Windsor | 0 | 11,999 | — | 12,192 | 11,999 | 193 | 1.6% | success |
| 25 | Trumbull | 0 | 12,014 | — | 12,151 | 12,014 | 137 | 1.1% | success |
| 26 | East Haven | 0 | 11,246 | — | 11,313 | 11,246 | 67 | 0.6% | success |
| 27 | Naugatuck | 0 | 10,719 | — | 11,540 | 10,719 | 821 | 7.1% | success |
| 28 | Farmington | 0 | 8,926 | — | 11,218 | 8,926 | 2,292 | 20.4% | success |
| 29 | Newtown | 0 | 10,956 | — | 11,228 | 10,956 | 272 | 2.4% | success |
| 30 | Cheshire | 0 | 10,779 | — | 10,950 | 10,779 | 171 | 1.6% | success |
| 31 | Guilford | 0 | 10,151 | — | 10,679 | 10,151 | 528 | 4.9% | success |
| 32 | Simsbury | 0 | 9,162 | — | 10,625 | 9,162 | 1,463 | 13.8% | success |
| 33 | Stonington | 0 | 9,361 | — | 10,190 | 9,361 | 829 | 8.1% | success |
| 34 | Southbury | 0 | 7,799 | — | 10,194 | 7,799 | 2,395 | 23.5% | success |
| 35 | Vernon | 0 | 9,426 | — | 10,080 | 9,426 | 654 | 6.5% | success |
| 36 | North Haven | 0 | 9,816 | — | 9,970 | 9,816 | 154 | 1.5% | success |
| 37 | East lyme | 0 | 9,170 | — | 9,518 | 9,170 | 348 | 3.7% | success |
| 38 | Watertown | 0 | 8,157 | — | 9,713 | 8,157 | 1,556 | 16.0% | success |
| 39 | Waterford | 0 | 9,089 | — | 9,366 | 9,089 | 277 | 3.0% | success |
| 40 | Bloomfield | 0 | 8,471 | — | 8,476 | 8,471 | 5 | 0.1% | success |
| 41 | Bethel | 0 | 6,941 | — | 7,805 | 6,941 | 864 | 11.1% | success |
| 42 | Darien | 0 | 5,242 | — | 7,602 | 5,242 | 2,360 | 31.0% | success |
| 43 | Brookfield | 0 | 7,340 | — | 7,520 | 7,340 | 180 | 2.4% | success |
| 44 | Plainville | 0 | 7,307 | — | 7,517 | 7,307 | 210 | 2.8% | success |
| 45 | New Canaan | 0 | 6,181 | — | 7,467 | 6,181 | 1,286 | 17.2% | success |
| 46 | WINCHESTER | 0 | 5,238 | 5,542 | 7,710 | 5,238 | 2,472 | 32.1% | success |
| 47 | New london | 0 | 6,582 | — | 7,297 | 6,582 | 715 | 9.8% | success |
| 48 | Old Saybrook | 0 | 6,232 | — | 7,061 | 6,232 | 829 | 11.7% | success |
| 49 | Clinton | 0 | 6,334 | — | 7,014 | 6,334 | 680 | 9.7% | success |
| 50 | Monroe | 0 | 7,684 | — | 8,339 | 7,684 | 655 | 7.9% | success |
| 51 | Wolcott | 0 | 6,690 | 6,784 | 6,809 | 6,690 | 119 | 1.7% | success |
| 52 | Coventry | 0 | 6,350 | — | 6,821 | 6,350 | 471 | 6.9% | success |
| 53 | Seymour | 0 | 6,042 | — | 6,650 | 6,042 | 608 | 9.1% | success |
| 54 | New Fairfield | 0 | 6,470 | 6,493 | 6,581 | 6,470 | 111 | 1.7% | success |
| 55 | Tolland | 0 | 6,328 | — | 6,523 | 6,328 | 195 | 3.0% | success |
| 56 | Colchester | 0 | 6,312 | — | 6,623 | 6,312 | 311 | 4.7% | success |
| 57 | Suffield | 0 | 6,199 | — | 6,420 | 6,199 | 221 | 3.4% | success |
| 58 | Wilton | 0 | 6,206 | — | 6,443 | 6,206 | 237 | 3.7% | success |
| 59 | Plainfield | 0 | 6,036 | — | 6,650 | 6,036 | 614 | 9.2% | success |
| 60 | East Hampton | 0 | 5,549 | — | 6,260 | 5,549 | 711 | 11.4% | success |
| 61 | Ellington | 0 | 5,952 | — | 6,098 | 5,952 | 146 | 2.4% | success |
| 62 | Cromwell | 0 | 873 | — | 6,138 | 873 | 5,265 | 85.8% | success |
| 63 | East Haddam | 0 | 5,445 | — | 5,896 | 5,445 | 451 | 7.6% | success |
| 64 | Orange | 0 | 5,673 | — | 6,089 | 5,673 | 416 | 6.8% | success |
| 65 | Ansonia | 0 | 5,755 | — | 5,782 | 5,755 | 27 | 0.5% | success |
| 66 | North Branford | 0 | 5,617 | — | 5,787 | 5,617 | 170 | 2.9% | success |
| 67 | Thompson | 0 | 4,893 | — | 5,611 | 4,893 | 718 | 12.8% | success |
| 68 | Windsor locks | 0 | 4,571 | — | 5,424 | 4,571 | 853 | 15.7% | success |
| 69 | Plymouth | 0 | 5,009 | — | 5,269 | 5,009 | 260 | 4.9% | success |
| 70 | Granby | 0 | 5,051 | — | 5,193 | 5,051 | 142 | 2.7% | success |
| 71 | Oxford | 0 | 4,958 | — | 5,099 | 4,958 | 141 | 2.8% | success |
| 72 | East windsor | 0 | 4,748 | — | 4,945 | 4,748 | 197 | 4.0% | success |
| 73 | Portland | 0 | 2,527 | — | 4,722 | 2,527 | 2,195 | 46.5% | success |
| 74 | Litchfield | — | — | — | — | — | — | — | skipped |
| 75 | Griswold | 0 | 4,358 | — | 4,679 | 4,358 | 321 | 6.9% | success |
| 76 | Haddam | 0 | 4,180 | — | 4,394 | 4,180 | 214 | 4.9% | success |
| 77 | Westbrook | 0 | 4,136 | — | 4,570 | 4,136 | 434 | 9.5% | success |
| 78 | Weston | 0 | 3,945 | — | 4,213 | 3,945 | 268 | 6.4% | success |
| 79 | Burlington | 0 | 3,945 | — | 4,027 | 3,945 | 82 | 2.0% | success |
| 80 | Canton | 0 | 3,870 | — | 3,963 | 3,870 | 93 | 2.3% | success |
| 81 | Somers | 0 | 3,824 | — | 3,865 | 3,824 | 41 | 1.1% | success |
| 82 | Woodbury | 0 | 3,800 | — | 3,866 | 3,800 | 66 | 1.7% | success |
| 83 | Prospect | 0 | 3,663 | — | 3,756 | 3,663 | 93 | 2.5% | success |
| 84 | Woodbridge | 0 | 3,604 | 3,721 | 3,628 | 3,604 | 24 | 0.7% | success |
| 85 | Brooklyn | 0 | 3,389 | — | 3,705 | 3,389 | 316 | 8.5% | success |
| 86 | Derby | 0 | 3,068 | — | 3,537 | 3,068 | 469 | 13.3% | success |
| 87 | New hartford | — | — | — | — | — | — | — | skipped |
| 88 | Middlebury | 0 | 3,091 | — | 3,459 | 3,091 | 368 | 10.6% | success |
| 89 | Thomaston | 0 | 2,986 | — | 3,337 | 2,986 | 351 | 10.5% | success |
| 90 | Harwinton | 0 | 2,963 | — | 3,372 | 2,963 | 409 | 12.1% | success |
| 91 | Easton | 0 | 2,449 | — | 3,563 | 2,449 | 1,114 | 31.3% | success |
| 92 | Durham | 0 | 3,046 | — | 3,180 | 3,046 | 134 | 4.2% | success |
| 93 | North stonington | 0 | 2,933 | — | 3,104 | 2,933 | 171 | 5.5% | success |
| 94 | Killingworth | 0 | 2,666 | — | 2,854 | 2,666 | 188 | 6.6% | success |
| 95 | Salisbury | 0 | 2,279 | — | 2,750 | 2,279 | 471 | 17.1% | success |
| 96 | Marlborough | 0 | 2,576 | — | 2,731 | 2,576 | 155 | 5.7% | success |
| 97 | Columbia | 0 | 2,585 | — | 2,635 | 2,585 | 50 | 1.9% | success |
| 98 | Sherman | 0 | 111 | — | 2,669 | 111 | 2,558 | 95.8% | success |
| 99 | Washington | 0 | 2,589 | — | 2,616 | 2,589 | 27 | 1.0% | success |
| 100 | Canterbury | 0 | 2,469 | — | 2,697 | 2,469 | 228 | 8.5% | success |
| 101 | Sharon | 0 | 2,252 | — | 2,522 | 2,252 | 270 | 10.7% | success |
| 102 | Bethany | 0 | 2,358 | — | 2,464 | 2,358 | 106 | 4.3% | success |
| 103 | Preston | 0 | 2,421 | — | 2,474 | 2,421 | 53 | 2.1% | success |
| 104 | Goshen | 0 | 2,217 | — | 2,304 | 2,217 | 87 | 3.8% | success |
| 105 | Ashford | 0 | 2,121 | — | 2,388 | 2,121 | 267 | 11.2% | success |
| 106 | Middlefield | 0 | 2,138 | — | 2,294 | 2,138 | 156 | 6.8% | success |
| 107 | Deep River | 0 | 2,113 | — | 2,218 | 2,113 | 105 | 4.7% | success |
| 108 | Beacon falls | 0 | 68 | — | 2,158 | 68 | 2,090 | 96.8% | success |
| 109 | East granby | 0 | 2,112 | — | 2,130 | 2,112 | 18 | 0.8% | success |
| 110 | Pomfret | 0 | 2,098 | — | 2,278 | 2,098 | 180 | 7.9% | success |
| 111 | Kent | 0 | 1,693 | — | 2,042 | 1,693 | 349 | 17.1% | success |
| 112 | Barkhamsted | 0 | 1,916 | 1,950 | 2,014 | 1,916 | 98 | 4.9% | success |
| 113 | Lisbon | 0 | 1,918 | — | 1,927 | 1,918 | 9 | 0.5% | success |
| 114 | Salem | 0 | 1,911 | — | 1,933 | 1,911 | 22 | 1.1% | success |
| 115 | Sterling | 0 | 1,752 | — | 1,817 | 1,752 | 65 | 3.6% | success |
| 116 | Bethlehem | 0 | 1,733 | — | 1,823 | 1,733 | 90 | 4.9% | success |
| 117 | North canaan | 0 | 1,549 | — | 1,706 | 1,549 | 157 | 9.2% | success |
| 118 | Andover | 0 | 1,538 | — | 1,700 | 1,538 | 162 | 9.5% | success |
| 119 | Roxbury | 0 | 1,447 | — | 1,530 | 1,447 | 83 | 5.4% | success |
| 120 | Bozrah | 0 | 1,136 | — | 1,391 | 1,136 | 255 | 18.3% | success |
| 121 | Cornwall | 0 | 1,259 | — | 1,394 | 1,259 | 135 | 9.7% | success |
| 122 | Morris | — | — | — | — | — | — | — | skipped |
| 123 | NORFOLK | 0 | 1,124 | — | 1,264 | 1,124 | 140 | 11.1% | success |
| 124 | Sprague | 0 | 1,186 | — | 1,279 | 1,186 | 93 | 7.3% | success |
| 125 | Eastford | 1 | 1,116 | — | 1,254 | 1,119 | 135 | 10.8% | success |
| 126 | Hampton | 0 | 1,059 | — | 1,228 | 1,059 | 169 | 13.8% | success |
| 127 | FRANKLIN | 0 | 1,057 | 1,102 | 1,111 | 1,057 | 54 | 4.9% | success |
| 128 | Warren | 0 | 1,035 | — | 1,087 | 1,035 | 52 | 4.8% | success |
| 129 | Colebrook | 0 | 906 | — | 999 | 906 | 93 | 9.3% | success |
| 130 | Canaan | — | — | — | — | — | — | — | skipped |
| 131 | Scotland | 0 | 818 | — | 906 | 818 | 88 | 9.7% | success |
| 132 | Union | 0 | 644 | — | 782 | 644 | 138 | 17.6% | success |
| 133 | Bridgeport | 0 | 1 | — | 28,061 | 27,711 | 350 | 1.2% | success |
| 134 | Middletown | 0 | 13,782 | — | 15,801 | 13,782 | 2,019 | 12.8% | success |
**How to refresh:** Re-run after a full 134-town run:
`python3 backend/scripts/data_import/134_towns/build_discrepancy_md.py backend/scripts/data_import/134_towns/logs/full_134_import_YYYYMMDD_HHMMSS.log`
Or with no args to use the latest full_134_import_*.log in that folder.
