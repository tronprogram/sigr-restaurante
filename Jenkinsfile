// =====================================================================
// CI/CD SIGR Restaurante - Pipeline declarativo de 12 etapas
// Gestion del Software (U3 AA2) + Calidad de Software
//
// Flujo: codigo -> calidad -> pruebas API -> imagen Docker -> pruebas E2E
//        -> SonarQube -> staging (:8001) -> aprobacion -> produccion (:8000) -> release tag
// =====================================================================
pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'MODO_DEMO',
            defaultValue: false,
            description: 'Pausa 1 s entre acciones de Selenium para verlas en http://localhost:7900'
        )
    }

    triggers {
        pollSCM('* * * * *')
    }

    options {
        skipDefaultCheckout()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        VENV         = '.venv'
        PYTHONUTF8   = '1'
        COVERAGE_MIN = '80'
        SELENIUM_URL = 'http://selenium:4444'
        RED_DOCKER   = 'ci'
    }

    stages {

        stage('1. Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty="Commit %h de %an: %s"'
                script {
                    env.VERSION = sh(
                        script: 'python3 -c "import app; print(app.__version__)"',
                        returnStdout: true
                    ).trim()
                    env.IMAGEN = "sigr-restaurante:${env.VERSION}-b${env.BUILD_NUMBER}"
                    env.CONTENEDOR_PRUEBAS = "sigr-pruebas"
                    env.PAUSA_DEMO = params.MODO_DEMO ? '1' : '0'
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.VERSION}"
                }
            }
        }

        stage('2. Preparar entorno') {
            steps {
                sh '''
                    python3 -m venv $VENV
                    . $VENV/bin/activate
                    pip install -q --upgrade pip
                    pip install -q -r requirements-dev.txt
                    mkdir -p reportes evidencias
                '''
            }
        }

        stage('3. Calidad de codigo') {
            parallel {
                stage('flake8 (estilo)') {
                    steps {
                        sh '. $VENV/bin/activate && python -m flake8 --output-file=reportes/flake8.txt --tee'
                    }
                }
                stage('bandit (seguridad)') {
                    steps {
                        sh '. $VENV/bin/activate && python -m bandit -r app --severity-level medium'
                    }
                }
            }
        }

        stage('4. Pruebas de API') {
            steps {
                sh '''
                    . $VENV/bin/activate
                    python -m pytest -m api --junitxml=reportes/junit-api.xml \
                        --cov=app --cov-report=xml:reportes/coverage.xml --cov-fail-under=$COVERAGE_MIN
                '''
            }
        }

        stage('5. Construir imagen') {
            steps {
                sh 'docker build -t "$IMAGEN" .'
            }
        }

        stage('6. Ambiente de pruebas') {
            steps {
                sh '''
                    docker rm -f "$CONTENEDOR_PRUEBAS" 2>/dev/null || true
                    docker run -d --name "$CONTENEDOR_PRUEBAS" --network "$RED_DOCKER" \
                        -e AMBIENTE=pruebas "$IMAGEN"
                '''
                esperarSalud(env.CONTENEDOR_PRUEBAS)
            }
        }

        stage('7. Pruebas de interfaz y E2E') {
            steps {
                sh '''
                    . $VENV/bin/activate
                    export BASE_URL="http://$CONTENEDOR_PRUEBAS:5000"
                    python -m pytest -m "ui or e2e" --junitxml=reportes/junit-ui.xml
                '''
            }
        }

        stage('8. SonarQube y Quality Gate') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('SonarQube') {
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                                -Dsonar.projectVersion=${env.VERSION} \
                                -Dsonar.qualitygate.wait=true
                        """
                    }
                }
            }
        }

        stage('9. Desplegar a staging') {
            steps {
                desplegar('staging', '8001')
            }
        }

        stage('10. Aprobacion') {
            steps {
                timeout(time: 30, unit: 'MINUTES') {
                    input message: "Staging tiene la v${env.VERSION} en http://localhost:8001. ¿Desplegar a produccion?",
                          ok: 'Desplegar'
                }
            }
        }

        stage('11. Desplegar a produccion') {
            steps {
                desplegar('produccion', '8000')
            }
        }

        stage('12. Release') {
            steps {
                withCredentials([gitUsernamePassword(credentialsId: 'github-token', gitToolName: 'Default')]) {
                    sh '''
                        git config user.name "Jenkins CI"
                        git config user.email "jenkins@sigr-restaurante.local"
                        if git ls-remote --exit-code --tags origin "v$VERSION" > /dev/null; then
                            echo "El tag v$VERSION ya existe: no se crea otro."
                        else
                            git tag -a "v$VERSION" -m "Release v$VERSION (build $BUILD_NUMBER)"
                            git push origin "v$VERSION"
                        fi
                    '''
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reportes/junit-*.xml'
            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reportes/coverage.xml']])
            recordIssues(enabledForFailure: true, tools: [flake8(pattern: 'reportes/flake8.txt')])
            archiveArtifacts artifacts: 'evidencias/*.png, reportes/**', allowEmptyArchive: true
            sh 'docker rm -f "$CONTENEDOR_PRUEBAS" 2>/dev/null || true'
        }
        success  { echo "OK: v${env.VERSION} desplegada en staging (:8001) y produccion (:8000)" }
        aborted  { echo 'Despliegue a produccion no aprobado: staging conserva la version nueva' }
        failure  { echo 'Fallo detectado: revisar la etapa en rojo, Test Result y evidencias en Artifacts' }
        cleanup  { cleanWs() }
    }
}

def esperarSalud(String contenedor) {
    withEnv(["OBJETIVO=${contenedor}"]) {
        sh '''
            for i in $(seq 1 30); do
                if curl -fs "http://$OBJETIVO:5000/api/salud"; then echo; exit 0; fi
                sleep 1
            done
            echo "La aplicacion no respondio a tiempo"; docker logs "$OBJETIVO"; exit 1
        '''
    }
}

def desplegar(String ambiente, String puerto) {
    withEnv(["AMB=${ambiente}", "PUERTO=${puerto}"]) {
        sh '''
            docker rm -f "sigr-$AMB" 2>/dev/null || true
            docker run -d --name "sigr-$AMB" --network "$RED_DOCKER" \
                -p "$PUERTO:5000" -e AMBIENTE="$AMB" --restart unless-stopped "$IMAGEN"
        '''
    }
    esperarSalud("sigr-${ambiente}")
    echo "v${env.VERSION} desplegada en ${ambiente}: http://localhost:${puerto}"
}
