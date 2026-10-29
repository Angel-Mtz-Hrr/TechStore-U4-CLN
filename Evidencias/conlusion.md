Reflexión

Tres errores encontrados y cómo los solucioné

1. **Python no estaba instalado.** Al ejecutar `python -m venv .venv` apareció "Python was not found". Lo resolví instalando Python (marcando la opción de agregarlo al PATH), cerrando y abriendo la terminal y verificando con `python --version`.

2. **No tenía permiso para subir archivos al repositorio.** GitHub mostraba "Las cargas están deshabilitadas" porque mi cuenta no tenía acceso push. Lo resolví haciendo un fork, subiendo mi carpeta ahí y abriendo un pull request al repositorio original.

3. **Confundí la documentación de Swagger con el resultado real.** No encontraba el código 409 porque miraba la sección "Responses", que solo muestra ejemplos. El resultado real está en "Server response", y el 409 solo aparece si se repite la misma operación con el mismo ID sin reiniciar el servidor, porque los datos viven en memoria.

Qué aprendí

Aprendí que la lógica de negocio debe vivir en el dominio (Order, Money, Specifications) y no en los endpoints, y que una operación inválida debe detenerse antes de cambiar el estado. También aprendí que las pruebas automáticas y los escenarios documentados sirven para comprobar que cada regla funciona y que falla correctamente.
