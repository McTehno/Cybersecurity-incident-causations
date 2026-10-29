Podatki



Splosno

\---

https://dashboard.shadowserver.org/#ddos

https://www.itu.int/itu-d/sites/cybersecurity

https://data.worldbank.org/

https://gotech.umd.edu/sites/default/files/2026-03/Cyber%20Events%20Database%20Codebook\_March%202026.pdf?utm\_source=chatgpt.com

https://gotech.umd.edu/cyber-events-database

https://www.ox.ac.uk/news/2024-04-10-world-first-cybercrime-index-ranks-countries-cybercrime-threat-level -> World-first 'Cybercrime Index' ranks countries by cybercrime threat level

https://www.netscout.com/ddos-attack-map

https://cert.pl/en/

ITU Global Cybersecurity Index by countries

https://www.csis.org/programs/strategic-technologies-program/significant-cyber-incidents





ZDA

\---



https://oag.ca.gov/privacy/databreach/list -> Organizacije, datumi incidentov, datumi prijav, obvestila o kršitvah podatkov

https://ocrportal.hhs.gov/ocr/breach/breach\_frontpage.jsf -> Incidenti v ameriškem zdravstvu, vrsta kršitve, število prizadetih oseb, zvezna država

https://github.com/vz-risk/VCDB  -> Podrobno klasificirani javno znani varnostni incidenti, metode napadov, žrtve in akterji

https://www.ic3.gov/AnnualReport/Reports - (Tukaj potrebujemo scraping) Letna porocila Prijave internetnega kriminala, vrste goljufij, finančne izgube, zvezne države

https://privacyrights.org/data-breaches -> Velika ameriška zbirka prijavljenih kršitev podatkov iz več državnih agencij (Dostop je questionable)



https://data.wa.gov/Consumer-Protection/Data-Breach-Notifications-Affecting-Washington-Res/sb4j-ca4h/about\_data -> Uradna zbirka zvezne države Washington, posodobljena oktobra 2026. Vsebuje statistične podatke iz prijav kršitev osebnih podatkov in omogoča prenos CSV, JSON ali XML. Ta zbirka bi bila še posebej dobra za raziskavo ransomware, podatkovnih kršitev in njihovih posledic. Ima tudi povezano zbirko o tem, katere vrste osebnih podatkov so bile razkrite.



Vprasanje: Ali se vrste in ciljni sektorji dokumentiranih kibernetskih incidentov v ZDA razlikujejo med zveznimi državami ter kako so povezani z njihovimi gospodarskimi in digitalnimi značilnostmi?





Slovenija

\---

https://www.cert.si/letna\_porocila -> Incidenti po letih, vrste incidentov, phishing, vdori, zlonamerna koda, goljufije

https://www.gov.si/novice/2024-10-18-polletno-porocilo-o-kibernetskih-incidentih-v-prvem-polletju-2024 -> Statistika SI-CERT in SIGOV-CERT, varnostni dogodki, javna uprava

https://www.cert.si/kibernetska-varnost-2025-v-stevilkah/ -> Spletne tabele in grafi Najnovejši letni pregled vrst in posledic incidentov

https://www.cert.si/statistika-si-cert-za-prvo-polovico-leta-2025/ -> Mesečne vrednosti in podrobnejša klasifikacija

https://www.policija.si/o-slovenski-policiji/statistika/kriminaliteta -> zbirka vsebuje vsa evidentirana kazniva dejanja, ne samo kibernetskih incidentov. Morali bi filtrirati relevantne pravne klasifikacije in preveriti, ali lahko ločimo vdore, napade na informacijske sisteme in spletne goljufije. Prav tako policijski zapis kaznivega dejanja ni nujno enak incidentu, ki ga beleži SI-CERT.



Deutschland

\---

https://konbriefing.com/en-topics/hacker-attacks-germany.html

https://www.statista.com/topics/10499/cyber-security-in-germany/?srsltid=AU7gw4XTVkeF0EHCtU87TIlz9C2Q1EIndx\_W-ZeRpr6rT-9w788N8dJY#topicOverview

https://www.bmi.bund.de/SharedDocs/pressemitteilungen/EN/2025/06/pm-lb-cybercrime-en.html

https://www.statista.com/statistics/1360141/cyber-crime-cases-recorded-police-germany/ (nimamo denar za to)

https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Publikationen/Lageberichte/Lagebericht2024.pdf?\_\_blob=publicationFile\&v=3



UK

\---

https://www.ncsc.gov.uk/collection/ncsc-annual-review-2025

https://www.gov.uk/government/statistics/cyber-security-breaches-survey-20252026

Information Commissioner's Office (ICO) - > https://ico.org.uk/action-weve-taken/complaints-and-concerns-data-sets/data-security-incident-trends

https://ico.org.uk/action-weve-taken/complaints-and-concerns-data-sets/cyber-investigations



France

\---







Kateri viri so najpomembnejši za nadaljevanje?

1

UK – Cyber Security Breaches Survey



Najbolj obetaven vir za neposredno kvantitativno analizo, ker ima uradne podatkovne tabele in informacije o sektorjih, velikosti organizacij ter vrstah groženj.

2

Nemčija – KonBriefing + BSI + BKA



Zanimiva kombinacija konkretnih javno znanih incidentov, gospodarskih sektorjev, nemških regij in uradnih nacionalnih statistik.



3

Francija – ANSSI + Cybermalveillance

Posebej obetavna za analizo vrst groženj, ciljnih sektorjev, ransomware in javne uprave.



4

Slovenija – SI-CERT + Policija



Dobra možnost za poglobljeno nacionalno študijo in regionalno analizo, če uspemo iz policijskih CSV izločiti ustrezna kazniva dejanja.



Kaj je treba preveriti pred dejanskim združevanjem?

Največja ovira ni dostopnost podatkov, ampak njihova primerljivost. Policijska statistika, incident CERT-a, kršitev osebnih podatkov in odgovor podjetja na anketo niso isti pojav.



Zato bi podatke vodila v treh ločenih skupinah: posamezni incidenti, agregirane nacionalne statistike in anketni podatki. Ne bi jih neposredno seštevala.



\------------------------------



Tri možne usmeritve raziskave

A. Široka primerjava nacionalnih profilov



Raziskovalno vprašanje: Ali gospodarska struktura in digitalizacija pojasnjujeta razlike v vrstah ter ciljnih sektorjih dokumentiranih incidentov med državami?



Odločitveno vprašanje: Katere kombinacije groženj in sektorjev naj imajo prednost pri preventivnih ukrepih?



Najbolje izkoristi svetovne in nacionalne podatke. Največ prostora za statistiko in strojno učenje.







B. Ransomware in kritični sektorji



Raziskovalno vprašanje: Kako se zastopanost ransomware med gospodarskimi sektorji razlikuje med ZDA, Nemčijo in Združenim kraljestvom ter kako se spreminja skozi čas?



Odločitveno vprašanje: Katerim sektorjem naj posamezna država nameni prednost pri zaščiti pred ransomware?



Bolj osredotočena raziskava, vendar zahteva kakovostne podatke o ransomware in posledicah.







C. Primerjava treh držav s svetovnimi pričakovanji



Raziskovalno vprašanje: Ali ZDA, Nemčija in Združeno kraljestvo odstopajo od profilov dokumentiranih incidentov, pričakovanih glede na njihove gospodarske in digitalne značilnosti?



Odločitveno vprašanje: Katerim grožnjam in sektorjem naj posamezna država nameni dodatno analitično pozornost glede na odstopanja od primerljivih držav?



Zanimivo za regresijo, napovedovanje in analizo odstopanj. Zahteva dovolj kakovosten svetovni vzorec.







Za odlocanje

\---

Za resno prioritizacijo potrebujemo tudi **podatke o posledicah, izpostavljenosti in stroških ukrepov.**





Ali imajo države z večjim deležem podjetij, ki uporabljajo določene zaščitne ukrepe, tudi manj podjetij z incidenti, ki povzročijo izgubo ali nedostopnost podatkov?



https://csrc.nist.gov/pubs/sp/1300/final



**isoc\_cisce\_ic – Incidenti in posledice**

\---

Ta zbirka nam pove kolikšen delež podjetij je doživel določen tip negativne posledice, ne koliko posameznih napadov je bilo izvedenih.



https://ec.europa.eu/eurostat/databrowser/view/isoc\_cisce\_ic/default/table?lang=en



Ali imajo države z večjim deležem dokumentiranih motilnih napadov v UMD tudi večji delež podjetij, ki poročajo o nedostopnosti storitev zaradi ransomware ali DoS?



**isoc\_cisce\_ra – Varnostni ukrepi in pripravljenost**



https://ec.europa.eu/eurostat/databrowser/view/isoc\_cisce\_ra/default/table?lang=en



Ta zbirka je za odločitveno analizo še posebej uporabna, ker pokaže razširjenost varnostnih praks.



**isoc\_cisce\_icn2 -  pregled posledic po gospodarskih dejavnostih**

**---**

kar se zelo dobro ujema z našim raziskovalnim vprašanjem o ciljnih sektorjih.

https://ec.europa.eu/eurostat/databrowser/view/isoc\_cisce\_icn2/default/table?lang=en





Katerim gospodarskim sektorjem in vrstam kibernetskih groženj je smiselno dati prednost pri načrtovanju zaščitnih ukrepov glede na zastopanost dokumentiranih incidentov, delež podjetij s škodljivimi posledicami in razširjenost obstoječih varnostnih ukrepov?

