# Afspraken voor Fortify-adapters

De Fortify-editie, versie, licentie, endpoints en het organisatiebeleid zijn nog niet gekozen. De twee componenten vereisen daarom expliciete adapters en falen als die ontbreken. Er is nog geen werkende Fortify-installatie; een ontbrekende scan wordt niet als geslaagd behandeld.

De losse scan- en gatecomponenten volgen onze oorspronkelijke keuze voor één taak per module. Fortify en GitLab verplichten deze opsplitsing niet. Bij activering beoordelen we eerst de ondersteunde integratie en of één component voor scan én beleidscontrole het gebruik eenvoudiger maakt.

Lever de adapters aan in de repository van de afnemer, of plaats een goedgekeurde implementatie in de componentimage en roep die aan met een repositoryscript. De scanimage heeft de Fortify-scanner/client, taaltools, POSIX `sh` en Python 3 nodig. De gate-image heeft alleen de client voor beleidscontrole, `sh` en Python 3 nodig. Deze images mogen verschillen.

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

De scancomponent controleert commit, pipeline, voltooiingsstatus en scan-ID. De outputvariabele verwijst naar het bewijsbestand. Dat bestand mag geen toegangsgegevens bevatten.

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

Geef een exitcode ongelijk aan nul terug bij beleidsovertredingen, authenticatie- of netwerkfouten, ontbrekende resultaten, onvoltooide scans en timeouts. Bij een mislukte beleidscontrole mag het rapport wel worden geschreven voor foutonderzoek. De gate-component weigert een succesrapport dat bij een andere scan hoort.

Als SSC-beleid de laatste status van een applicatieversie controleert, gebruik dan aparte versies per pipeline/commit of voer upload, verwerking en beleidscontrole als één vergrendelde reeks uit. Alleen de uploadjob vergrendelen is onvoldoende: een andere pipeline kan de versie vóór de beleidscontrole wijzigen. Bewaar de provider-ID's en controleer of het beleidsresultaat bij het bewijsbestand hoort. Beoordeel altijd de bedoelde scan.

Het officiële `fcli ssc action run ci` kan het aanbieden en afhandelen van scans aansturen. De actie `check-policy` is gedocumenteerd als voorbeeld; pas het echte organisatiebeleid aan en beheer het onder versiebeheer. Schakel optionele PR/MR-reacties in deze adapters alleen in als dat expliciet gewenst is. Gebruik voor Fortify on Demand de bijbehorende FoD-API's/acties en vertaal hun resultaten naar dezelfde afspraken. Zie [Fortify SSC-acties](https://fortify.github.io/fcli/latest/ssc-actions.html).
