# Afspraken voor Fortify-adapters

**Status: TODO.** Dit is een voorbereidende adapterafspraak voor [modules/todo/fortify.yml](../modules/todo/fortify.yml), geen actieve demo-integratie. Zie [de modulestatus](modules.md#todo-nog-niet-actief).

De Fortify-editie, versie, licentie, endpoints en het organisatiebeleid zijn nog niet gekozen. De component `fortify` vereist daarom expliciete scan- en gateadapters en faalt als die ontbreken. Er is nog geen werkende Fortify-installatie; een ontbrekende scan wordt niet als geslaagd behandeld.

Eén component voert scan en beleidscontrole in dezelfde job uit. De afnemer kiest één image en geeft `scan-adapter` en `gate-adapter` op. Er is geen aparte gatejob of overdracht via een `receipt-variable` nodig. Dit adaptercontract is voorlopig maatwerk van deze bibliotheek. Beoordeel vóór activering de ondersteunde Fortify-integratie en vervang de adapters als die de benodigde taak rechtstreeks afhandelt.

Lever de adapters aan in de repository van de afnemer, of plaats een goedgekeurde implementatie in de componentimage en roep die aan met een repositoryscript. De gekozen image bevat de Fortify-scanner, de client voor beleidscontrole, benodigde taaltools, POSIX `sh` en Python 3.

De scanadapter wordt vanuit de werkmap van de component aangeroepen:

```sh
sh ci/fortify/scan.sh \
  --receipt /absolute/output/scan.json \
  --commit COMMIT_SHA \
  --pipeline-id PIPELINE_ID
```

De adapter moet de huidige broncode aanbieden, wachten tot de verwerking klaar is en een JSON-bewijsbestand schrijven:

```json
{
  "schema_version": 1,
  "provider": "ssc",
  "scan_id": "immutable-scan-or-artifact-id",
  "application_version_id": "provider-specific-id",
  "commit_sha": "the-exact-CI_COMMIT_SHA",
  "pipeline_id": "the-exact-CI_PIPELINE_ID",
  "status": "completed"
}
```

De component controleert commit, pipeline, voltooiingsstatus en scan-ID voordat de beleidscontrole begint. Het bewijsbestand mag geen toegangsgegevens bevatten.

De aparte adapter voor beleidscontrole wordt zo aangeroepen:

```sh
sh ci/fortify/gate.sh \
  --receipt /absolute/input/scan.json \
  --report /absolute/output/policy.json
```

Deze adapter moet precies de scan uit het bewijsbestand aan het goedgekeurde beleid toetsen en het volgende resultaat schrijven:

```json
{
  "scan_id": "same-immutable-scan-or-artifact-id",
  "policy_version": "security-policy-2026-01",
  "status": "passed"
}
```

Geef een exitcode ongelijk aan nul terug bij beleidsovertredingen, authenticatie- of netwerkfouten, ontbrekende resultaten, onvoltooide scans en timeouts. Bij een mislukte beleidscontrole mag het rapport wel worden geschreven voor foutonderzoek. De component weigert een succesrapport dat bij een andere scan hoort. Pas nadat beide stappen slagen, publiceert zij `FORTIFY_RECEIPT`, `FORTIFY_REPORT` en `FORTIFY_STATUS=passed`. De post-hook draait dan één keer. Scan- en beleidsrapporten worden ook bij fouten als artifacts bewaard, voor zover ze zijn aangemaakt.

Als SSC-beleid de laatste status van een applicatieversie controleert, gebruik dan aparte versies per pipeline/commit of voer upload, verwerking en beleidscontrole als één vergrendelde reeks uit. Alleen de uploadjob vergrendelen is onvoldoende: een andere pipeline kan de versie vóór de beleidscontrole wijzigen. Bewaar de provider-ID's en controleer of het beleidsresultaat bij het bewijsbestand hoort. Beoordeel altijd de bedoelde scan.

Het officiële `fcli ssc action run ci` kan het aanbieden en afhandelen van scans aansturen. De actie `check-policy` is gedocumenteerd als voorbeeld; pas het echte organisatiebeleid aan en beheer het onder versiebeheer. Schakel optionele PR/MR-reacties in deze adapters alleen in als dat expliciet gewenst is. Gebruik voor Fortify on Demand de bijbehorende FoD-API's/acties en vertaal hun resultaten naar dezelfde afspraken. Zie [Fortify SSC-acties](https://fortify.github.io/fcli/latest/ssc-actions.html).
