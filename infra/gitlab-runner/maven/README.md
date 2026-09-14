# Maven-image voor de wrapper

Deze image voegt `unzip` toe aan de vastgezette Maven/Java-image. De `only-script` Maven Wrapper van de testapplicatie gebruikt een ZIP-distributie met een SHA-256-controle. Zonder `unzip` kiest deze wrapper een tarbestand; dat heeft een andere checksum. De checksumcontrole blijft ingeschakeld.

`./infra/setup.sh install` bouwt deze Maven-image en de daarop gebaseerde Sonar-image voor de architectuur van Docker Desktop. De installer publiceert beide naar de lokale Artifactory en stelt de digestreferenties in voor de applicatie en samples. De referenties staan in het gegenereerde `infra/artifactory/ci-images.json`.

De Docker-buildcontext bevat alleen de Dockerfile. Zie [Apache Maven Wrapper](https://maven.apache.org/tools/wrapper/) voor de distributie- en checksuminstellingen.
