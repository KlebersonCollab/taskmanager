# Exemplo: Integração Django + TaskManager

Este exemplo demonstra como plugar o **TaskManager** em um projeto Django via `taskmanager.contrib.django`.

---

## ⚙️ Configuração no Django

1. Adicione `'taskmanager.contrib.django'` ao seu `INSTALLED_APPS` em `settings.py`:
```python
INSTALLED_APPS = [
    ...,
    "taskmanager.contrib.django",
    "meu_app",
]
```

2. Em qualquer app do Django, crie um arquivo `tasks.py` decorando suas funções com `@task`:
```python
# sample_app/tasks.py
from taskmanager import task

@task(name="billing.generate_invoices", queue="billing")
async def generate_invoices(month: int, year: int):
    ...
```
*(O `taskmanager.contrib.django` descobre e carrega automaticamente todos os módulos `tasks.py` de todos os `INSTALLED_APPS`!)*

3. Adicione a rota no `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    path("tasks/", include("taskmanager.contrib.django.urls")),
]
```

---

## 🚀 Comandos de Gerenciamento

Execute os workers e schedulers diretamente com o `manage.py`:

```bash
# Iniciar worker consumindo filas específicas:
python samples/django_sample/manage.py run_worker --queues billing,default --concurrency 4

# Iniciar o scheduler de cron do Django:
python samples/django_sample/manage.py run_scheduler
```
