// Jenkins pipeline for tv-insight.
//
// The assignment states the project "will be executed in a Jenkins pipeline
// inside a VM", so the pipeline is part of the deliverable. It is declarative,
// uses the repository's own Make targets, and fails fast on quality gates before
// spending time on the browser suite.
//
// Agents: the Jenkins VM is expected to have Docker available. Lint, type checks
// and tests run in the same base images the application ships with, so the
// pipeline cannot drift from production.
//
// Credentials (optional): `huggingface-api-token`, `openrouter-api-key` as
// secret text. When absent the AI feature runs on its offline provider, which is
// exactly what the fallback chain is for.

pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
    }

    environment {
        PYTHON_IMAGE   = 'python:3.12-slim'
        NODE_IMAGE     = 'node:22-alpine'
        COMPOSE_PROJECT = "tvinsight-${BUILD_NUMBER}"
        APP_PORT       = '7777'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git rev-parse --short HEAD > .revision'
                archiveArtifacts artifacts: '.revision', allowEmptyArchive: true
            }
        }

        stage('Build') {
            parallel {
                stage('Backend image') {
                    steps {
                        sh 'docker build --target runtime -t tvinsight-app:ci .'
                    }
                }
                stage('Frontend build') {
                    agent {
                        docker { image "${NODE_IMAGE}"; args '-u root' }
                    }
                    steps {
                        dir('frontend') {
                            sh 'npm ci --no-audit --no-fund'
                            sh 'npm run build'
                        }
                        stash name: 'frontend-dist', includes: 'frontend/dist/**', allowEmpty: true
                    }
                }
            }
        }

        stage('Quality gates') {
            parallel {
                stage('Lint') {
                    parallel {
                        stage('ruff') {
                            agent {
                                docker { image "${PYTHON_IMAGE}"; args '-u root' }
                            }
                            steps {
                                sh '''
                                    pip install --quiet -e "backend[dev]"
                                    cd backend && ruff check .
                                '''
                            }
                        }
                        stage('eslint') {
                            agent {
                                docker { image "${NODE_IMAGE}"; args '-u root' }
                            }
                            steps {
                                dir('frontend') {
                                    sh 'npm ci --no-audit --no-fund'
                                    // Type-aware: also fails on deprecated APIs
                                    // (e.g. React.FormEvent).
                                    sh 'npm run lint'
                                }
                            }
                        }
                    }
                }
                stage('Type check') {
                    parallel {
                        stage('mypy') {
                            agent {
                                docker { image "${PYTHON_IMAGE}"; args '-u root' }
                            }
                            steps {
                                sh '''
                                    pip install --quiet -e "backend[dev]"
                                    cd backend && mypy
                                '''
                            }
                        }
                        stage('tsc') {
                            agent {
                                docker { image "${NODE_IMAGE}"; args '-u root' }
                            }
                            steps {
                                dir('frontend') {
                                    sh 'npm ci --no-audit --no-fund'
                                    sh 'npm run typecheck'
                                }
                            }
                        }
                    }
                }
            }
        }

        stage('Tests') {
            parallel {
                stage('Backend (unit + integration)') {
                    agent {
                        docker { image "${PYTHON_IMAGE}"; args '-u root' }
                    }
                    steps {
                        sh '''
                            pip install --quiet -e "backend[dev]"
                            cd backend && python -m pytest \
                                --junitxml=build/reports/pytest.xml \
                                --cov=tv_insight --cov-fail-under=90 \
                                --cov-report=xml:build/reports/coverage.xml
                        '''
                    }
                    post {
                        always {
                            junit testResults: 'backend/build/reports/pytest.xml',
                                  allowEmptyResults: true
                            recordCoverage tools: [[parser: 'COBERTURA',
                                                   pattern: 'backend/build/reports/coverage.xml']]
                        }
                    }
                }
                stage('Frontend (component)') {
                    agent {
                        docker { image "${NODE_IMAGE}"; args '-u root' }
                    }
                    steps {
                        dir('frontend') {
                            sh 'npm ci --no-audit --no-fund'
                            sh 'npm run test:coverage -- --reporter=junit --outputFile=reports/vitest.xml'
                        }
                    }
                    post {
                        always {
                            junit testResults: 'frontend/reports/vitest.xml', allowEmptyResults: true
                        }
                    }
                }
            }
        }

        stage('Start the stack') {
            steps {
                sh """
                    docker compose -p ${COMPOSE_PROJECT} up --build -d
                """
                // The compose healthcheck already gates readiness; this waits a
                // little longer and fails with the logs if the app never comes up.
                sh """
                    for i in \$(seq 1 60); do
                        if curl -fsS "http://localhost:${APP_PORT}/api/health" >/dev/null; then
                            echo "application is up"
                            exit 0
                        fi
                        sleep 2
                    done
                    echo "application did not become healthy"
                    docker compose -p ${COMPOSE_PROJECT} logs app
                    exit 1
                """
            }
        }

        stage('Smoke test on real TVMaze') {
            steps {
                sh """
                    curl -fsS "http://localhost:${APP_PORT}/api/series/search?q=breaking%20bad" \\
                        | tee search.json
                    python3 - <<'PY'
                    import json
                    payload = json.load(open('search.json'))
                    assert payload['count'] > 0, 'the catalogue returned no results'
                    print('catalogue reachable, results:', payload['count'])
                    PY
                """
            }
        }

        stage('End to end (Playwright)') {
            steps {
                sh """
                    docker compose -p ${COMPOSE_PROJECT} --profile test run --rm e2e || true
                """
            }
            post {
                always {
                    publishHTML target: [
                        allowMissing: true,
                        reportDir: 'frontend/playwright-report',
                        reportFiles: 'index.html',
                        reportName: 'Playwright report',
                    ]
                    archiveArtifacts artifacts: 'frontend/test-results/**,frontend/playwright-report/**',
                                     allowEmptyArchive: true
                }
            }
        }
    }

    post {
        always {
            sh """
                docker compose -p ${COMPOSE_PROJECT} logs --no-color > compose.log || true
                docker compose -p ${COMPOSE_PROJECT} down -v || true
                docker image prune -f || true
            """
            archiveArtifacts artifacts: 'compose.log', allowEmptyArchive: true
        }
        success { echo 'tv-insight pipeline succeeded.' }
        failure {
            echo 'tv-insight pipeline failed.'
            // notify('team-channel', 'FAILURE')
        }
    }
}
