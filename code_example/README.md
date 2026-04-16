# Iniciar el Proyecto

Sigue estos pasos para levantar y ejecutar el proyecto de Django utilizando Docker.

## Levantar la Aplicación

Levanta los contenedores en segundo plano:

```bash
docker compose up --build -d
```

Si los contenedores ya están construidos previamente, puedes simplemente ejecutar:

```bash
docker compose up -d
```

Verifica que los servicios estén corriendo:

```bash
docker compose ps
```

Accede al contenedor de la aplicación:

```bash
docker compose exec app bash
```

Navega al directorio del proyecto Django:

```bash
cd solicitudes
```

Inicia el servidor de desarrollo de Django:

```bash
python manage.py runserver 0:8000
```

La aplicación estará disponible en:
[http://localhost:8000](http://localhost:8000)

Para detener y eliminar los contenedores:

```bash
docker compose down
```

---

## Ejecución de Pruebas

El proyecto cuenta con pruebas unitarias (usando el framework de Django) y pruebas de aceptación (implementadas con Behave).

### Pruebas Unitarias

Las pruebas unitarias se enfocan en validar la lógica y las validaciones internas del código, como funciones, modelos o formularios.

**Ejemplo:** Validar que el método `calcular_total()` de un modelo funcione correctamente.

```python
# solicitudes/tests/test_models.py
from django.test import TestCase
from solicitudes.models import Solicitud

class SolicitudModelTest(TestCase):
    def test_calculo_total_correcto(self):
        solicitud = Solicitud.objects.create(cantidad=5, precio_unitario=20)
        total = solicitud.calcular_total()
        self.assertEqual(total, 100)
```

**Ejecutar todas las pruebas unitarias:**

```bash
python manage.py test
```

**Ejecutar una prueba unitaria específica (por ejemplo, de formularios):**

```bash
python manage.py test tipo_solicitudes.tests.tests_forms
```

Esto ejecutará únicamente las pruebas definidas dentro del archivo `tests_forms.py` en la app `tipo_solicitudes`.

### Pruebas de Aceptación

Las pruebas de aceptación validan la funcionalidad completa del sistema, simulando la interacción del usuario con los flujos reales de la aplicación.
En este proyecto se implementan con Behave, siguiendo el enfoque BDD (Behavior Driven Development), donde las pruebas se describen en lenguaje natural (`.feature`).

Las pruebas se encuentran en:

```
solicitudes/pruebas_aceptacion/
```

**Ejemplo de archivo .feature:**

```gherkin
Feature: Envío de solicitudes
  Como usuario
  Quiero enviar una solicitud
  Para que el sistema la registre correctamente

  Scenario: Crear una nueva solicitud
    Given que el usuario está en el formulario de solicitudes
    When completa los datos requeridos y envía el formulario
    Then la solicitud se guarda exitosamente en la base de datos
```

**Ejemplo de pasos en Python (`steps/solicitud_steps.py`):**

```python
from behave import given, when, then
from django.urls import reverse
from django.test import Client
from solicitudes.models import Solicitud

@given('que el usuario está en el formulario de solicitudes')
def step_impl(context):
    context.client = Client()

@when('completa los datos requeridos y envía el formulario')
def step_impl(context):
    context.response = context.client.post(reverse('crear_solicitud'), {
        "nombre": "Esmeralda Espino",
        "cantidad": 3,
        "precio_unitario": 50
    })

@then('la solicitud se guarda exitosamente en la base de datos')
def step_impl(context):
    assert context.response.status_code == 302
    assert Solicitud.objects.filter(nombre="Esmeralda Espino").exists()
```

**Ejecutar pruebas de aceptación con Behave:**

```bash
python manage.py behave solicitudes/pruebas_aceptacion
```