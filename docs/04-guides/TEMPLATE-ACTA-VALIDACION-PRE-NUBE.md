# TEMPLATE - Acta de Validación Pre-Nube (GO/NO-GO)

## 1) Metadatos de la corrida

- Fecha (YYYY-MM-DD):
- Hora local:
- Responsable:
- Rama git:
- Commit SHA:
- Entorno objetivo (`dev/staging/prod`):

---

## 2) Evidencias técnicas

### 2.1 Tests

Comando:
```bash
make test
```

Resultado:
- Estado (`OK/NO`):
- Evidencia corta (ej. `10 passed`):

### 2.2 Terraform formato

Comando:
```bash
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform fmt -check -recursive
```

Resultado:
- Estado (`OK/NO`):
- Evidencia corta:

### 2.3 Terraform inicialización

Comando:
```bash
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform init -backend=false
```

Resultado:
- Estado (`OK/NO`):
- Evidencia corta (ej. `Terraform has been successfully initialized!`):

### 2.4 Terraform validación

Comando:
```bash
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform validate
```

Resultado:
- Estado (`OK/NO`):
- Evidencia corta (ej. `Success! The configuration is valid.`):

### 2.5 Barrido de secretos

Comando:
```bash
rg -n "sk-proj-|AKIA|BEGIN PRIVATE KEY" -S . --glob '!docs/04-guides/GUIDE-DEPLOY-AWS.md'
```

Resultado:
- Estado (`OK/NO`):
- Evidencia corta (ej. `sin hallazgos`):

### 2.6 CI y guías

Controles:
- `.github/workflows/ci.yml` existe.
- `GUIDE-DEPLOY-AWS.md`, `GUIDE-MIGRATION-LOCAL-TO-CLOUD.md` y `GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md` actualizadas.

Resultado:
- Estado (`OK/NO`):
- Evidencia corta:

---

## 3) Decisión de readiness

- Resultado consolidado (`GO/NO-GO`):
- Riesgos abiertos (si aplica):
- Acciones pendientes antes de nube:

---

## 4) Autorizaciones

1. Autorización para actualizar repositorio GitHub (`SI/NO`):
2. Autorización para iniciar proceso de nube AWS (`SI/NO`):

---

## 5) Firma de cierre

- Responsable técnico:
- Fecha/hora:
- Observaciones finales:
