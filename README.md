
# Forex OANDA Bot v7x

AI-powered automated trading bot for OANDA — LightGBM + TCN + GARCH + Drift Monitoring

## Quick Start

1. cp .env.example .env
2. nano .env  # Fill OANDA_TOKEN, ACCOUNT_ID
3. chmod +x deploy.sh
4. ./deploy.sh init
5. ./deploy.sh train
6. ./deploy.sh daemon
