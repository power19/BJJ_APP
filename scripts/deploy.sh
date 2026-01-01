#!/bin/bash
# Deployment script for Invictus BJJ Management System

set -e

echo "==================================="
echo "Invictus BJJ Deployment Script"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Determine docker compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Parse arguments
ACTION=${1:-"up"}

case $ACTION in
    "build")
        echo -e "${YELLOW}Building Docker image...${NC}"
        $COMPOSE_CMD build --no-cache
        echo -e "${GREEN}Build complete!${NC}"
        ;;

    "up")
        echo -e "${YELLOW}Starting services...${NC}"
        $COMPOSE_CMD up -d
        echo -e "${GREEN}Services started!${NC}"
        echo ""
        echo "App is running at: http://localhost:8000"
        ;;

    "down")
        echo -e "${YELLOW}Stopping services...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}Services stopped!${NC}"
        ;;

    "restart")
        echo -e "${YELLOW}Restarting services...${NC}"
        $COMPOSE_CMD restart
        echo -e "${GREEN}Services restarted!${NC}"
        ;;

    "logs")
        $COMPOSE_CMD logs -f
        ;;

    "status")
        $COMPOSE_CMD ps
        ;;

    "update")
        echo -e "${YELLOW}Pulling latest changes and rebuilding...${NC}"
        git pull
        $COMPOSE_CMD build
        $COMPOSE_CMD up -d
        echo -e "${GREEN}Update complete!${NC}"
        ;;

    "production")
        echo -e "${YELLOW}Starting production with Nginx...${NC}"
        $COMPOSE_CMD --profile production up -d
        echo -e "${GREEN}Production services started!${NC}"
        echo ""
        echo "App is running at: http://localhost (port 80)"
        ;;

    *)
        echo "Usage: $0 {build|up|down|restart|logs|status|update|production}"
        echo ""
        echo "Commands:"
        echo "  build      - Build Docker image"
        echo "  up         - Start services (default)"
        echo "  down       - Stop services"
        echo "  restart    - Restart services"
        echo "  logs       - View logs"
        echo "  status     - Show service status"
        echo "  update     - Pull latest code and rebuild"
        echo "  production - Start with Nginx reverse proxy"
        exit 1
        ;;
esac
