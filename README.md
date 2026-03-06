# PQR Hybrid Lakehouse

Repositorio del MVP analitico PQRS con arquitectura por planos (Control/Data/Compute).

## Guia general del proyecto

Manual principal desde cero hasta nube:
- [GUIDE-PQR-HYBRID-LAKEHOUSE](docs/04-guides/GUIDE-PQR-HYBRID-LAKEHOUSE.md)

## Inicio rapido local

```bash
make env
make test
```

Guias clave:
- [Guia operacion local](docs/04-guides/GUIDE-OPERACION-LOCAL-COMANDOS.md)
- [Guia ETL y Prefect](docs/04-guides/GUIDE-ETL-POR-ETAPAS-Y-ORQUESTACION-PREFECT.md)
- [Guia dashboard analitica](docs/04-guides/GUIDE-DASHBOARD-Y-APP-ANALITICA-PQRS.md)
- [Guia migracion local a cloud](docs/04-guides/GUIDE-MIGRATION-LOCAL-TO-CLOUD.md)
- [Guia deploy AWS](docs/04-guides/GUIDE-DEPLOY-AWS.md)
- [Guia Terraform baseline y roadmap](docs/04-guides/GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md)

## Base AWS por IaC

Baseline Terraform:
- [infra/aws/terraform/README](infra/aws/terraform/README.md)
