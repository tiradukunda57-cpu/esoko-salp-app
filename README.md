# E-Soko SALP - urubuga rumwe kuri buri wese

Link imwe (urugero `https://esoko-salp.onrender.com`). Umuntu yinjira ahandi hamwe, sisitemu imujyana kuri dashboard ye:

| Uruhare | Aho ajya | Uko yinjira |
|---|---|---|
| Umuhinzi / Umworozi | `/farmer` | Kode ya SMS (nta jambo ry'ibanga) |
| Umuguzi | `/buyer` | Telefone + ijambo ry'ibanga, cyangwa kode ya SMS |
| Agent / ushinzwe irembo | `/agent` | Telefone + ijambo ry'ibanga |
| Admin / SuperAdmin (wowe) | `/admin` | Telefone + ijambo ry'ibanga |
| Leta | `/dashboard` | Telefone + ijambo ry'ibanga |
| Isuzuma rya USSD (ikizamini gusa) | `/ussd-demo` | Nta kwinjira |

Ururimi (Kinyarwanda / English / Français) rurahindurwa hejuru ku rupapuro rwose. Kwiyandikisha 500 Frw, komisiyo 2%, checkup Kabiri na Gatanu saa 19:00, amatungo yose n'ibihingwa byose, n'ibyangombwa bya Leta byongerwamo **mu rubuga (Admin > Amategeko ya Leta), nta guhindura code**.

## Ibyagerageje n'ibitaragerageza (ukuri)

| Igice | Imiterere |
|---|---|
| Ubucuruzi bwose (kwiyandikisha, escrow, Agent, payout, komisiyo, checkup, kode z'irembo, amategeko ya Leta, USSD) | Tests 53 zirarangira neza |
| Impapuro zose z'urubuga | Zageragejwe muri browser nyayo (Chromium) kuva kwinjira kugeza kwishyura umuhinzi, no kuri telefone, dark mode n'igifaransa |
| SQL kuri PostgreSQL (Neon) | Amabwiriza 180 yose yemewe na PostgreSQL 16 nyayo (`tests/pg_validate.py`) |
| Gukorana na Neon nyirizina (`psycopg2`) | **Ntirageragezwa nyirizina** (aho nakoreye nta internet ya PyPI). Niba ikosa ribaye ubwa mbere, rizagaragara muri Render > Logs - ndarikosora |
| Kwishyura kwa MoMo/Airtel nyakuri | **Ntibirabaho.** Hari kwigana gusa. Bisaba umufatanyabikorwa ufite uruhushya |
| USSD (*801#) na SMS nyakuri | **Bisaba umukoresha w'itumanaho** (MTN/Airtel/aggregator). Kuri Render free hari gutinda (reba hepfo) |

**Uru rubuga rushyirwaho ari "ikizamini" (`ESOKO_ENV=demo`):** ubwishyu n'SMS ni ibyo kwigana, nta mafaranga nyayo anyura. Ntugashyiremo Indangamuntu nyayo.

## Gushyira kuri interineti (nta Terminal)

### 1. Neon: database itarangira (iminota 5)
1. Jya kuri https://neon.tech ukore konti (Sign up, ushobora gukoresha Google/GitHub). Nta karita ya banki.
2. **New project** > Izina: `esoko` > Postgres 16 > Region: **AWS Europe (Frankfurt)**. Kanda **Create**.
3. Ku rupapuro rw'umushinga kanda **Connect**. Hitamo "**Pooled connection**" (ishyiraho akamenyetso). 
4. Kopora umurongo utangira na `postgresql://...` (kanda "Copy snippet"/ijisho ubanze uwurebe). Ubike ahantu hizewe, **ntukawohereze mu butumwa**. Ni wo `DATABASE_URL`.

### 2. GitHub: shyiramo code (rimwe gusa)
Hitamo **imwe**:
- **A (yoroshye):** Fungura `https://github.com/tiradukunda57-cpu/esoko-salp` > **Add file > Upload files** > fungura zip nshya ku Mac, ukurure **ibiri imbere muri folder** yayo (`app`, `tests`, `render.yaml`, `Dockerfile`, `requirements.txt`, `README.md`, `.github`...) hanyuma **Commit changes**. Niba `.github` itagaragara ku Mac (ni folder ihishwe), kanda Cmd+Shift+. muri Finder.
- **B (byiza ku gihe kizaza):** Muri Claude: Settings > Connectors > huza konti ya GitHub. Nyuma yaho nshobora gusunika impinduka ubwanjye.

### 3. Render: shyiraho urubuga (iminota 10)
1. https://render.com > Sign up with GitHub > emerera Render kubona repo `esoko-salp`.
2. **New > Blueprint** > hitamo `esoko-salp` > Render isoma `render.yaml`.
3. Irakubaza agaciro k'ibi bine, uzuza:
   - `DATABASE_URL` = umurongo wa Neon (intambwe 1)
   - `ESOKO_BOOTSTRAP_NAME` = amazina yawe
   - `ESOKO_BOOTSTRAP_PHONE` = telefone yawe (urugero 07XXXXXXXX)
   - `ESOKO_BOOTSTRAP_PASSWORD` = ijambo ry'ibanga rirerire (nibura 8)
   - `ESOKO_SETTLEMENT_MSISDN` na `ESOKO_SUPPORT_PHONE` = numero yo kwakira amafaranga n'iy'ubufasha (format +2507XXXXXXXX)
4. **Apply**. Utegereje iminota 3-5 kugeza ubone "Live". Link yawe iri hejuru ku rupapuro (`https://esoko-salp-xxxx.onrender.com`).
5. Niba Blueprint itakoze: **New > Web Service** > repo > Runtime Python > Region Frankfurt > Instance **Free** > Build `pip install -r requirements.txt` > Start `uvicorn app.api:app --host 0.0.0.0 --port $PORT` > shyiramo amabanga yo muri `render.yaml` mu "Environment".

### 4. Injira nka SuperAdmin (wowe)
1. Fungura link yawe > **Injira** > telefone + ijambo ry'ibanga washyizeho > ujyanwa kuri `/admin`.
2. **Ako kanya:** muri Render > serivisi > **Environment** > siba `ESOKO_BOOTSTRAP_PASSWORD` > Save. (Konti yawe isanzwe ibitswe muri database.)
3. Admin > **Imidugudu**: shyiramo imidugudu (umudugudu, akagali, umurenge, akarere - umurongo umwe ku mudugudu).
4. Admin > **Abantu** > **Ongeraho umukozi**: kora Agent (n'umurenge we), ushinzwe irembo, Admin, Leta.

### 5. Igenzura rya Kabiri na Gatanu saa 19:00 (GitHub Actions)
Render free ntigira cron, GitHub ni yo ihamagara urubuga.
1. Render > Environment > kopora agaciro ka `ESOKO_JOB_SECRET`.
2. GitHub > repo > **Settings > Secrets and variables > Actions > New repository secret**: 
   - `APP_URL` = link yawe ya Render (nta `/` ku iherezo)
   - `JOB_SECRET` = agaciro wakopoye
3. Kugerageza: **Actions > scheduled-jobs > Run workflow** (job: `checkup`). Ugomba kubona icyatsi.

## Uko wowe nka SuperAdmin ureba muri database

**Muri rubuga ubwo (byoroshye):** Admin > **Database**. 
- Ubona tableau zose n'umubare w'imirongo. Kanda imwe urebe imirongo (25 kuri page), shakisha, manura **CSV** ufungure muri Excel.
- Ni ugusoma gusa. Amagambo y'ibanga n'ibimenyetso by'Indangamuntu **ntibigaragara**. Buri kureba karandikwa muri **Ibyakozwe** (activity log).
- Admin isanzwe ntibona iyi tab.

**Kuri Neon (inyongera):** https://console.neon.tech > umushinga `esoko` > **Tables** (kureba/guhindura) cyangwa **SQL Editor** (SQL yawe, urugero `SELECT status, COUNT(*) FROM products GROUP BY status;`). Ibi ni ibyawe wenyine; ugire amakenga mu guhindura.

## Kuvugurura (nta Terminal)
1. Impinduka zose ziza muri GitHub (nsunika ubwanjye nyuma yo guhuza GitHub na Claude, cyangwa ukoreshe "Upload files" / ikaramu y'iguhindura kuri github.com).
2. Render ihita **yubaka kandi igashyiraho ivugurura ubwayo** (~3 min). Amakuru ntabura kuko abitse kuri Neon.
3. Reba imiterere: Render > Events/Logs.

## Imbibi za Render free (ukuri)
- Urubuga **rusinzira nyuma y'iminota 15** nta muntu; ubwa mbere bwo kubyuka bufata ~1 min. Abantu bazabona gutinda gato.
- **USSD ntishobora kwizerwa kuri free**: telecom itegereza amasegonda make, kubyuka bikarenza. Mbere yo gutangira nyakuri: Render Starter (~$7/ukwezi) ntisinzira.
- Amasaha 750 ku kwezi arahagije serivisi imwe.
- Neon free: 1 GB kuri buri mushinga, ntirangira, kandi isinzira nyuma y'iminota 5 (kubyuka ~1 s).

## Gutangira nyakuri (ESOKO_ENV=prod)
Bisaba: umufatanyabikorwa wo kwishyura wemewe, SMS/USSD nyakuri, Render yishyurwa, amategeko yo kurinda amakuru. `ESOKO_ENV=prod` ihagarika ibikoresho byo kwigana kandi igakeneye amabanga nyayo yose.

## Gukorera kuri Mac (ntibisabwa)
`python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.api:app --reload` hanyuma ufungure http://127.0.0.1:8000
Tests: `python3 -m unittest discover -s tests`
