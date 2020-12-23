#! groovy

currentBuild.displayName = "Availability Canary [$currentBuild.number]"

FUNC_NAME="availability-canary"
String commitHash = ""

try {
    if (ISSUE_NUMBER)
        echo "Building from pull request..."
} catch (Exception ignored) {
    ISSUE_NUMBER = false
    echo "Building from jenkins job..."
}

pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr:'10'))
        disableConcurrentBuilds()
        quietPeriod(1)
    }
    parameters {
        booleanParam(name: 'DeleteExisting', defaultValue: false, description: 'Delete existing stack?')
        booleanParam(name: 'Deploy', defaultValue: true, description: 'Deploy latest artifact')
    }
    stages {

        stage("Checkout") {
            steps {
                script {
                    prTools.checkoutBranch(ISSUE_NUMBER, "vizzyy-org/$FUNC_NAME")
                    commitHash = env.GIT_COMMIT.substring(0,7)
                }
            }
        }

        stage("Delete Stack") {
            when {
                expression {
                    return env.DeleteExisting == "true"
                }
            }
            steps {
                script {
                    sh("aws cloudformation delete-stack --stack-name $FUNC_NAME")
                    sh("aws cloudformation wait stack-delete-complete --stack-name $FUNC_NAME")
                }
            }
        }

        stage("Zip") {
            steps {
                script {
                    sh("zip -r lambda_function.zip availability-canary.py mysql* google proto* six* -q")
                }
            }
        }

        stage("Package") {
            steps {
                script {
                    sh("/usr/local/bin/sam package --s3-bucket vizzyy-packaging --output-template-file packaged.yml")
                }
            }
        }

        stage("Deploy") {
            when {
                expression {
                    return env.Deploy == "true"
                }
            }
            steps {
                script {
                    sh("/usr/local/bin/sam deploy --template-file packaged.yml --stack-name $FUNC_NAME --capabilities CAPABILITY_IAM")
                }
            }
        }

    }
    post {
        success {
            script {
                sh "echo '${env.GIT_COMMIT}' > ~/userContent/$FUNC_NAME-last-success-hash.txt"
                echo "SUCCESS"
            }
        }
        failure {
            script {
                echo "FAILURE"
            }
        }
        cleanup { // Cleanup post-flow always executes last
            deleteDir()
        }
    }
}