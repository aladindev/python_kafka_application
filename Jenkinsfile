// python JenkinsFile
// Pipeline: Declarative 파이프라인 설치 해결
// This Pipeline has run successfully, but does not define any stages. Please use the stage step to define some stages in this Pipeline.
// git clone -> .py -> Pulbish Over SSH
// sourceFiles: '**/*.py'
//  stage('List Files') {
//     steps {
//         script {
//             sh 'ls -la' // Unix/Linux 환경의 경우
//             // bat 'dir' // Windows 환경의 경우
//         }
//     }
// } 
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                // Git 저장소에서 최신 코드를 가져옵니다.
                git url: 'https://github.com/aladindev/python_kafka_application.git', branch: 'main'
            }
        }

        stage('Deploy') {
            steps {
                script {
                    // SCP를 사용하여 파일을 서버에 배포합니다. 
                    // 환경 변수를 사용하여 서버 정보를 참조합니다.
                    //sh "ssh -v ${env.SERVER_USER}@${env.SERVER_IP}"
                    echo ${env.SERVER_IP}
                    sh "ssh ${env.SERVER_USER}@${env.SERVER_IP}"
                    sh "scp -r ./* ${env.SERVER_USER}@${env.SERVER_IP}:${env.SERVER_DIR}"
                }
            }
        }
    }
    post {
        success {
            echo 'Deployment is successful!'
        }

        failure {
            echo 'Deployment failed.'
        }
    }
}
