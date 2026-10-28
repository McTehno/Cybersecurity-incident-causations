A. Raziskave o vrstah napadov, njihovih vzrokih in tarčah

**1. Zakaj so nekateri gospodarski sektorji pogosteje tarče?**

ENISA Threat Landscape 2026 — 22. september 2026

Raziskovalna vprašanja, ki jih obravnavajo takšne analize:

\- Kateri sektorji so najpogosteje tarče dokumentiranih incidentov?

\- Ali se vrste napadov razlikujejo med javnim sektorjem, bankami, industrijo in zdravstvom?

\- Ali so motivi napadalcev povezani z izbranim sektorjem?

\- Ali se struktura napadov spreminja skozi čas?

Katere podatke uporabljajo? Dokumentirane incidente, datum napada, ciljni sektor, vrsto grožnje, motiv in informacije o napadalcih.



ENISA je ugotovila, da so javne ustanove posebej izpostavljene ideološko motiviranim DDoS napadom. Kar 82 % evidentiranih dogodkov v tem sektorju je bilo povezanih z DDoS. To pomeni, da pogostost napadov ni nujno neposredna mera finančne privlačnosti sektorja.



**B.Ali lahko iz vrste incidenta, sektorja in države sklepamo, kdo napada in zakaj?**

University of Maryland — Cyber Events Database 2.0, 2026

Raziskovalci na University of Maryland so razvili podatkovno zbirko za sistematično proučevanje globalnih kibernetskih incidentov.

16.382		175		1.431

incidentov	držav		akterjev



(Stanje podatkov februarja 2026, navedeno v raziskovalnem poročilu, objavljenem junija 2026. )



Podatki med drugim vsebujejo državo žrtve, vrsto napadalca, motiv, sektor in učinek incidenta.

Njihove opisne analize kažejo, da so kriminalne skupine zelo pomembna kategorija akterjev ter da sta javna uprava in zdravstvo med pogosto dokumentiranimi tarčami. Zabeležili so tudi povečanje motečih oziroma disruptivnih napadov leta 2022, povezano z rusko invazijo na Ukrajino.



To odpira bolj poglobljena vprašanja: Ali sta motiv napadalca in izbira sektorja povezana? Ali so države, ki so geopolitično izpostavljene, pogosteje tarče disruptivnih napadov kot kraje podatkov?





**C.Katere poti napadalci najpogosteje uporabljajo za vdor?**

Verizon — Data Breach Investigations Report 2026

**(https://www.verizon.com/business/resources/reports/dbir/)**

Tu raziskovalce zanima nekaj drugega kot ENISA: ne samo, **kdo je napaden, ampak kako pride do uspešnega vdora.**

Vprašanja vključujejo: *Ali imajo človeške napake večjo vlogo kot tehnične ranljivosti? Ali se pomen phishinga spreminja? Kako pogosto so napadi povezani z zunanjimi dobavitelji?*

Verizon uporablja podatke o dejanskih varnostnih incidentih in potrjenih vdorih, ki jih prispevajo različne organizacije, preiskovalci, zavarovalnice in varnostne ekipe.

V poročilu 2026 je izpostavil naslednje ugotovitve:

31 % Vdorov se je začelo z izkoriščanjem programskih ranljivosti.



48 % Vdorov je vključevalo ransomware.



Raziskovalna nadaljevanja bi lahko bila: **Ali imajo manjša podjetja drugačne poti začetnega vdora kot velike organizacije? Ali je uporaba ranljivosti bolj razširjena v sektorjih s starejšo informacijsko infrastrukturo?**



D. **Ali lahko napovemo, katere ranljivosti bodo napadalci dejansko izkoristili?**

FIRST — Exploit Prediction Scoring System (EPSS)

**https://www.first.org/epss/**

To je zelo dober primer raziskave, ki združuje strojno učenje, statistiko in odločanje.

Osrednje vprašanje: Katera javno znana programska ranljivost bo najverjetneje izkoriščena v naslednjih 30 dneh?

Raziskovalci uporabljajo podatke o ranljivostih (CVE), objavljeni kodi za izkoriščanje ranljivosti, dejavnosti napadalcev in dejanskem izkoriščanju.

Njihova pomembna ugotovitev je, da je velik delež ranljivosti redko oziroma nikoli zaznano izkoriščen, medtem ko je izkoriščanje koncentrirano v manjšem delu ranljivosti. Zato popravljanje vseh ranljivosti samo po splošni oceni resnosti ni nujno najučinkovitejše. Model EPSS ocenjuje verjetnost izkoriščanja v naslednjih 30 dneh.



Odločitveno vprašanje: **Katere ranljivosti moramo odpraviti najprej, če imamo na voljo samo določeno število ur dela?**

To je tudi odličen primer, kako se rezultat podatkovne analitike uporabi za odločitev.

Podatki: FIRST EPSS — brezplačen CSV in API.





Ali je gospodarska razvitost države povezana z njenim profilom kibernetskih groženj?

Ali geopolitični dogodki spreminjajo vrste kibernetskih napadov?

Ali države in organizacije z večjimi varnostnimi naložbami dosegajo boljšo zaščito?



https://www.enisa.europa.eu/topics/cyber-threats/threat-landscape

https://spp.umd.edu/research-impact/publications/university-marylands-cyber-events-database-20-systematic-framework

https://www.verizon.com/business/resources/reports/dbir/





DATA -

The Ransomware Decade — Sarabi et al. (2025)

https://iplists.firehol.org/

https://globaldatalab.org/

https://databank.worldbank.org/

https://zenodo.org/records/15571866

https://datacatalogue.ukdataservice.ac.uk/studies/study/8480#details



Katere dodatne zbirke potrebujeva?

1\. World Bank – World Development Indicators: BDP na prebivalca, prebivalstvo, delež industrije, storitev in uporaba interneta.

2\. ITU – Global Cybersecurity Index: nacionalna kibernetska pripravljenost, pri čemer morava preveriti razpoložljive letnike in metodološko primerljivost.

3\. EuRepoC: dodatni incidenti za primerjavo geografske pokritosti, vrst napadov in ciljnih sektorjev z UMD.

Pozneje lahko dodava Shadowserver za kazalnike tehnične izpostavljenosti, če bodo primerni za primerjavo držav.







\-------------------------------------

Zakaj je ransomware med dokumentiranimi incidenti proizvodnega sektorja bolj zastopan in katere značilnosti teh napadov so povezane z njihovimi posledicami?

KAJ BI ODKRILI?

V nekaterih državah in obdobjih odkrijemo povečano zastopanost disruptivnih incidentov.

NOVO RAZISKOVALNO VPRAŠANJE

Ali je ta sprememba časovno povezana z določenimi geopolitičnimi dogodki?

PREDLAGANA ANALIZA

Časovne vrste, primerjava dogodkov in dodatni viri.



KAJ BI ODKRILI?

V določenem sektorju odkrijemo izrazito visok delež ransomware med dokumentiranimi incidenti.

NOVO RAZISKOVALNO VPRAŠANJE

Ali se načini vdora, napadalne skupine in posledice ransomware napadov razlikujejo med tem sektorjem in drugimi?

PREDLAGANA ANALIZA

The Ransomware Decade, analiza sektorjev, regresija.



KAJ BI ODKRILI?

Nekatere države močno odstopajo od držav s primerljivo stopnjo gospodarske razvitosti.

NOVO RAZISKOVALNO VPRAŠANJE

Katere značilnosti teh držav lahko dodatno pojasnijo odstopanja?

PREDLAGANA ANALIZA

Analiza ostankov modela, detekcija odstopanj, dodatni kazalniki.



KAJ BI ODKRILI?

Države z višjo uporabo interneta imajo drugačno sestavo incidentov tudi po upoštevanju BDP.

NOVO RAZISKOVALNO VPRAŠANJE

Ali je povezava prisotna v vseh sektorjih in ali ostane stabilna skozi čas?

PREDLAGANA ANALIZA

UMD + World Bank + ITU, regresija in časovne primerjave.

