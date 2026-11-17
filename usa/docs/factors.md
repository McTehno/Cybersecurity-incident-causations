
# USA National Factors — Definitions and Methodology

Ten indicators used to analyze relationships between economic conditions, digitalization, and publicly documented cyber incidents in the United States.

- **Data period:** 2014–2025
- **Correlation period:** 2014–2024 (11 complete observations)
- **Dataset:** `data/processed/factors/usa_national_factors_2014_2025.csv`

## 1. Cyber Incidents

### `incident_rate` — Documented incident rate

Number of publicly documented cyber incidents per 100,000 residents.

$$
\text{Incident rate} =
\frac{N_{\text{documented incidents}}}{P_{\text{USA}}}
\times 100\,000
$$

- **Unit:** Incidents per 100,000 residents
- **Source:** UMD Cyber Events Database + World Bank population (`SP.POP.TOTL`)
- **Note:** Measures documented incidents, not all actual cyberattacks.

## 2. Economic Development

### `gdp_per_capita` — GDP per capita

Economic output per resident, measured in current US dollars.

$$
\text{GDP per capita} = \frac{\text{GDP}}{\text{Population}}
$$

- **Unit:** Current USD per person
- **Source:** World Bank (`NY.GDP.PCAP.CD`)
- **Note:** Not adjusted for inflation.

### `gdp_growth` — Annual GDP growth

Annual percentage change in real GDP.

$$
\text{GDP growth}_t =
\frac{\text{Real GDP}_t-\text{Real GDP}_{t-1}}
{\text{Real GDP}_{t-1}}
\times 100
$$

- **Unit:** %
- **Source:** World Bank (`NY.GDP.MKTP.KD.ZG`)

## 3. Economic Structure

### `industry_gdp_pct` — Industry share of GDP

Contribution of industry to total economic output.

$$
\text{Industry share} =
\frac{\text{Industry value added}}{\text{GDP}}
\times 100
$$

- **Unit:** % of GDP
- **Source:** BEA, `SAGDP2`
- **Included LineCodes:** 6, 10, 11, 12

### `services_gdp_pct` — Services share of GDP

Contribution of services to total economic output.

$$
\text{Services share} =
\frac{\text{Services value added}}{\text{GDP}}
\times 100
$$

- **Unit:** % of GDP
- **Source:** BEA, `SAGDP2`
- **Included LineCodes:** 34, 35, 36, 45, 50, 59, 68, 75, 82, 83

**Note:** Industry and services are components of the same GDP total and are not independent.

## 4. Labor Market

### `unemployment_rate` — Unemployment rate

Percentage of the labor force that is unemployed.

$$
\text{Unemployment rate} =
\frac{\text{Unemployed persons}}{\text{Labor force}}
\times 100
$$

- **Unit:** %
- **Source:** World Bank (`SL.UEM.TOTL.ZS`), modeled ILO estimate

### `labor_force_participation` — Labor force participation

Percentage of the population aged 15+ participating in the labor force.

$$
\text{Participation rate} =
\frac{\text{Labor force}}{\text{Population aged 15+}}
\times 100
$$

- **Unit:** %
- **Source:** World Bank (`SL.TLF.CACT.ZS`), modeled ILO estimate

## 5. Business Activity

### `establishment_density` — Establishment density

Number of business establishments per 10,000 residents.

$$
\text{Establishment density} =
\frac{\sum_{s=1}^{50} N_{\text{establishments},s}}
{\sum_{s=1}^{50} P_s}
\times 10\,000
$$

- **Unit:** Establishments per 10,000 residents
- **Source:** BLS QCEW + state population data
- **Coverage:** 50 US states, excluding Washington, D.C.
- **Note:** Establishments are not equivalent to unique companies or newly created businesses.

## 6. Digitalization

### `internet_users_pct` — Internet users

Percentage of individuals using the internet.

$$
\text{Internet users} =
\frac{\text{Individuals using the internet}}
{\text{Total population}}
\times 100
$$

- **Unit:** % of population
- **Source:** World Bank (`IT.NET.USER.ZS`)
- **Available:** 2014–2024

### `fixed_broadband_per_100` — Fixed broadband subscriptions

Number of fixed broadband subscriptions per 100 residents.

$$
\text{Fixed broadband} =
\frac{N_{\text{fixed broadband subscriptions}}}
{\text{Total population}}
\times 100
$$

- **Unit:** Subscriptions per 100 residents
- **Source:** World Bank (`IT.NET.BBND.P2`)
- **Available:** 2014–2024
- **Note:** Measures subscriptions, not the percentage of individuals with broadband access.

## 7. Methodological Notes

- All ten indicators are available for **2014–2024**.
- Internet usage and fixed broadband data are missing for 2025.
- Incident rate uses the total US population; establishment density covers only the 50 states.
- BEA sector shares are used instead of the World Bank sector shares for consistency across 2014–2025.
- Correlations describe associations, not causation.
- With only 11 annual observations, results require careful interpretation and sensitivity checks.

## 8. Data Sources

- [UMD Cyber Events Database](https://cissm.umd.edu/research-impact/publications/cyber-events-database)
- [World Bank — World Development Indicators](https://databank.worldbank.org/source/world-development-indicators)
- [BEA — Regional GDP Data](https://www.bea.gov/itable/regional-gdp-and-personal-income)
- [BLS — Quarterly Census of Employment and Wages](https://www.bls.gov/cew/)

## 9. Processing Scripts

- `src/download_data/download_world_bank.py`
- `src/data_processing/world_bank_io.py`
- `src/data_processing/bea_national_sector_shares.py`
- `src/data_processing/qcew_national_establishment_density.py`
- `src/data_processing/umd_national_incident_rate.py`
- `src/data_processing/build_usa_national_factors.py`
