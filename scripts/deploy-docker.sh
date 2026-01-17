#!/bin/bash
#
# Polymarket AutoTrader - Docker Deployment Script
#
# This script automates the complete deployment of the trading bot in Docker.
# It handles configuration, building, and starting the services.
#
# Usage:
#   ./scripts/deploy-docker.sh           # Interactive deployment
#   ./scripts/deploy-docker.sh --build   # Force rebuild
#   ./scripts/deploy-docker.sh --stop    # Stop all services
#   ./scripts/deploy-docker.sh --logs    # Show logs
#   ./scripts/deploy-docker.sh --status  # Show status

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
ENV_FILE="$PROJECT_ROOT/.env"

# Functions
print_header() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker installed: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "Install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Start Docker: sudo systemctl start docker"
        exit 1
    fi
    print_success "Docker daemon running"
}

# Check configuration
check_configuration() {
    print_header "Checking Configuration"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found"
        echo ""
        echo "Would you like to run the setup wizard? (y/n)"
        read -r answer
        
        if [ "$answer" = "y" ]; then
            python3 "$SCRIPT_DIR/setup.py"
        else
            print_error "Cannot deploy without configuration"
            echo "Run: python scripts/setup.py"
            exit 1
        fi
    fi
    
    # Validate configuration
    if python3 "$SCRIPT_DIR/setup.py" --validate; then
        print_success "Configuration valid"
    else
        print_error "Configuration invalid"
        echo "Run: python scripts/setup.py"
        exit 1
    fi
}

# Build Docker images
build_images() {
    print_header "Building Docker Images"
    
    cd "$PROJECT_ROOT"
    
    echo "Building bot image..."
    docker build -t polymarket-bot:latest -f docker/Dockerfile .
    
    print_success "Images built successfully"
}

# Start services
start_services() {
    print_header "Starting Services"
    
    cd "$PROJECT_ROOT"
    
    # Determine which compose command to use
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Check if Telegram is configured
    TELEGRAM_TOKEN=$(grep -E "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" | cut -d'=' -f2)
    
    if [ -n "$TELEGRAM_TOKEN" ] && [ "$TELEGRAM_TOKEN" != "" ]; then
        print_info "Telegram configured - starting with telegram service"
        $COMPOSE_CMD -f docker/docker-compose.yml --profile telegram up -d
    else
        print_info "Starting bot service only"
        $COMPOSE_CMD -f docker/docker-compose.yml up -d bot
    fi
    
    print_success "Services started"
    
    # Show status
    echo ""
    $COMPOSE_CMD -f docker/docker-compose.yml ps
}

# Stop services
stop_services() {
    print_header "Stopping Services"
    
    cd "$PROJECT_ROOT"
    
    if docker compose version &> /dev/null; then
        docker compose -f docker/docker-compose.yml down
    else
        docker-compose -f docker/docker-compose.yml down
    fi
    
    print_success "Services stopped"
}

# Show logs
show_logs() {
    cd "$PROJECT_ROOT"
    
    if docker compose version &> /dev/null; then
        docker compose -f docker/docker-compose.yml logs -f "${1:-bot}"
    else
        docker-compose -f docker/docker-compose.yml logs -f "${1:-bot}"
    fi
}

# Show status
show_status() {
    print_header "Service Status"
    
    cd "$PROJECT_ROOT"
    
    if docker compose version &> /dev/null; then
        docker compose -f docker/docker-compose.yml ps
    else
        docker-compose -f docker/docker-compose.yml ps
    fi
    
    echo ""
    print_info "Recent logs:"
    echo ""
    
    if docker compose version &> /dev/null; then
        docker compose -f docker/docker-compose.yml logs --tail=20 bot
    else
        docker-compose -f docker/docker-compose.yml logs --tail=20 bot
    fi
}

# Backup data
backup_data() {
    print_header "Backing Up Data"
    
    BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Copy state files from volumes
    docker cp polymarket-bot:/app/state "$BACKUP_DIR/state" 2>/dev/null || true
    docker cp polymarket-bot:/app/simulation "$BACKUP_DIR/simulation" 2>/dev/null || true
    
    # Backup .env (without private key!)
    grep -v "PRIVATE_KEY" "$ENV_FILE" > "$BACKUP_DIR/.env.backup" 2>/dev/null || true
    
    print_success "Backup saved to: $BACKUP_DIR"
}

# Update deployment
update_deployment() {
    print_header "Updating Deployment"
    
    # Pull latest code (if using git)
    if [ -d "$PROJECT_ROOT/.git" ]; then
        print_info "Pulling latest code..."
        cd "$PROJECT_ROOT"
        git pull
    fi
    
    # Rebuild and restart
    stop_services
    build_images
    start_services
    
    print_success "Deployment updated"
}

# Main
main() {
    cd "$PROJECT_ROOT"
    
    case "${1:-}" in
        --build)
            check_prerequisites
            check_configuration
            build_images
            ;;
        --stop)
            stop_services
            ;;
        --logs)
            show_logs "${2:-bot}"
            ;;
        --status)
            show_status
            ;;
        --backup)
            backup_data
            ;;
        --update)
            check_prerequisites
            check_configuration
            update_deployment
            ;;
        --help)
            echo "Polymarket AutoTrader - Docker Deployment"
            echo ""
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  (no option)  Interactive deployment"
            echo "  --build      Build Docker images only"
            echo "  --stop       Stop all services"
            echo "  --logs       Show logs (optional: service name)"
            echo "  --status     Show service status"
            echo "  --backup     Backup state and data"
            echo "  --update     Pull latest and redeploy"
            echo "  --help       Show this help"
            ;;
        *)
            # Interactive deployment
            print_header "Polymarket AutoTrader - Docker Deployment"
            
            check_prerequisites
            check_configuration
            
            echo ""
            echo "This will deploy the trading bot in Docker."
            echo ""
            echo "Options:"
            echo "  1) Deploy (build and start)"
            echo "  2) Rebuild and restart"
            echo "  3) View logs"
            echo "  4) Check status"
            echo "  5) Stop services"
            echo "  6) Backup data"
            echo "  0) Exit"
            echo ""
            read -p "Select option: " choice
            
            case $choice in
                1)
                    build_images
                    start_services
                    ;;
                2)
                    stop_services
                    build_images
                    start_services
                    ;;
                3)
                    show_logs
                    ;;
                4)
                    show_status
                    ;;
                5)
                    stop_services
                    ;;
                6)
                    backup_data
                    ;;
                0)
                    echo "Exiting..."
                    exit 0
                    ;;
                *)
                    print_error "Invalid option"
                    exit 1
                    ;;
            esac
            ;;
    esac
}

main "$@"
