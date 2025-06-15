#!/bin/bash
# Build and manage Intelligence Engine Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="intelligence-engine"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="intelligence-engine"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

build_image() {
    print_info "Building Intelligence Engine Docker image..."
    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
    print_info "Image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
}

run_container() {
    print_info "Starting Intelligence Engine container..."
    
    # Check if container is already running
    if [ "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
        print_warning "Container ${CONTAINER_NAME} is already running"
        return
    fi
    
    # Remove old container if exists
    if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
        print_info "Removing old container..."
        docker rm ${CONTAINER_NAME}
    fi
    
    # Run container
    docker run -d \
        --name ${CONTAINER_NAME} \
        -p 50051:50051 \
        -p 8080:8080 \
        -v $(pwd)/config:/app/config:ro \
        -v intelligence-models:/app/models \
        -v $(pwd)/logs:/app/logs \
        -e INTELLIGENCE_LOG_LEVEL=INFO \
        ${IMAGE_NAME}:${IMAGE_TAG}
    
    print_info "Container started successfully"
}

stop_container() {
    print_info "Stopping Intelligence Engine container..."
    docker stop ${CONTAINER_NAME} || true
    print_info "Container stopped"
}

logs() {
    docker logs -f ${CONTAINER_NAME}
}

shell() {
    print_info "Opening shell in container..."
    docker exec -it ${CONTAINER_NAME} /bin/bash
}

test_grpc() {
    print_info "Testing gRPC connection..."
    docker exec ${CONTAINER_NAME} python -c "
import grpc
from pkg.intelligence.proto import intelligence_pb2_grpc, intelligence_pb2

channel = grpc.insecure_channel('localhost:50051')
stub = intelligence_pb2_grpc.IntelligenceServiceStub(channel)
response = stub.HealthCheck(intelligence_pb2.Empty())
print(f'Health check: {response.healthy}')
print(f'Version: {response.version}')
print(f'Components: {dict(response.components)}')
"
}

compose_up() {
    print_info "Starting services with docker-compose..."
    docker-compose up -d
    print_info "Services started. Access Grafana at http://localhost:3000 (admin/admin)"
}

compose_down() {
    print_info "Stopping services..."
    docker-compose down
}

# Main script
case "$1" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        stop_container
        run_container
        ;;
    logs)
        logs
        ;;
    shell)
        shell
        ;;
    test)
        test_grpc
        ;;
    compose-up)
        compose_up
        ;;
    compose-down)
        compose_down
        ;;
    *)
        echo "Usage: $0 {build|run|stop|restart|logs|shell|test|compose-up|compose-down}"
        echo ""
        echo "Commands:"
        echo "  build        - Build Docker image"
        echo "  run          - Run container"
        echo "  stop         - Stop container"
        echo "  restart      - Restart container"
        echo "  logs         - Show container logs"
        echo "  shell        - Open shell in container"
        echo "  test         - Test gRPC connection"
        echo "  compose-up   - Start all services with docker-compose"
        echo "  compose-down - Stop all services"
        exit 1
        ;;
esac