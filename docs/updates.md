# Actualizaciones del complemento

El canal usa el mecanismo estándar del gestor de complementos: `browser_specific_settings.gecko.update_url`, JSON HTTPS y XPI versionado de GitHub Releases, con SHA-256. No hay código propio que descargue o ejecute instaladores.

La versión 0.1.1 no incluye update_url: debe instalarse manualmente una vez la versión 0.1.2. A partir de ella, Thunderbird puede consultar `updates.json` y aplicar futuras versiones compatibles si las actualizaciones del complemento están habilitadas. No se afirma que una actualización automática real haya ocurrido hasta probar una transición entre versiones.

El canal publicado conserva el ID técnico de la instalación inicial para actualizar el mismo complemento. El ID no es una credencial. No se distribuyen rutas, cuentas permitidas, correos ni secretos: desde 0.1.2 el complemento solicita el scope al host nativo local mediante bootstrap. El host lo obtiene de runtime/config.json, excluido del repositorio y de releases.

Una instalación nueva genera otro ID y debe configurar su propio canal o usar paquetes locales. El paquete del canal inicial no sustituye al instalador ni debe copiarse entre perfiles. La vinculación sigue siendo por instalación; la API pública no permite atestar la ruta del perfil.

## Preparar una release

1. Actualizar versión de package.json, server.js e install.ps1. Revisar compatibilidad del protocolo y permisos.
2. Probar código, host y complemento. Regenerar con install.ps1: preserva ID, genera XPI sin config.js y updates.json con hash del artefacto exacto.
3. Revisar archivos Git y contenido ZIP. Excluir runtime, configuraciones generadas, datos de correo, registros locales y secretos.
4. Subir código, etiqueta y release GitHub con XPI; publicar updates.json únicamente cuando el artefacto esté disponible. No reutilizar archivos de una versión anterior ni sobrescribir etiquetas.
5. Verificar GET público del JSON y XPI, ID/version/HTTPS/hash y contenido ZIP.
6. En Thunderbird usar Buscar actualizaciones y verificar addonVersion, reconexión y epoch nuevo. No reutilizar referencias del epoch anterior.

El canal actualiza solo el complemento. Cambios de host o MCP requieren actualizar el checkout e instalar localmente; no se introducen privilegios remotos para hacerlo. Solo publicar versiones compatibles con el host instalado o coordinar previamente la migración. Rollback: instalar el XPI conocido anterior; escrituras inciertas deben reconciliarse sin replay.

Fuente: [Mozilla: Updating your extension](https://extensionworkshop.com/documentation/manage/updating-your-extension/).
