# Thunderbird Local Private MCP

Versión 0.1.3. Implementación local para Windows con MailExtension MV3, Native Messaging, named pipe y cliente MCP stdio. Thunderbird conserva OAuth2, certificados y sincronización. No se leen contraseñas ni se modifican sus bases de datos.

## Estado verificado

- 24 herramientas MCP; pruebas del protocolo MCP y validación de argumentos.
- 21 pruebas Node, 4 pruebas Python y transporte real Windows con complemento simulado: PASS.
- Dependencias npm: 0 vulnerabilidades conocidas según `npm audit --omit=dev` al 2026-10-05.
- Host registrado para el usuario actual; runtime protegido por ACL; XPI generado.
- Complemento 0.1.2 activo en Thunderbird 157.0.1: conexión, cuentas/carpetas, búsquedas sin unread, lectura Gmail/Outlook y cabeceras/EML de las tres cuentas IMAP verificados. Unread y HTML-only corregidos y verificados en 0.1.1. No se han cambiado mensajes.

La implementación todavía no cumple todas las pruebas de aceptación del diseño. Un complemento simulado no demuestra compatibilidad ni efectos de sincronización en Thunderbird.

## Activación

El perfil y cuentas permitidas se seleccionan explicitamente en la instalacion. Se excluye la cuenta de carpetas unificadas. El instalador vincula una instalación a un ID aleatorio y una lista explícita de cuentas. La API pública no permite demostrar la ruta del perfil en runtime: `profileBinding=installation` declara esa limitación. No copiar el XPI a otro perfil.

1. En Thunderbird, abre Complementos y temas, menú de engranaje, **Instalar complemento desde archivo**. Selecciona `dist/thunderbird-local-mcp-0.1.3.xpi` y revisa los permisos. No requiere desactivar la comprobación de firmas globalmente.
2. Añade el servidor del archivo `runtime/mcp-client.json` al cliente MCP. Es configuración stdio local: no hay puerto ni túnel.
3. Comprueba `get_status`, versión/epoch y `list_accounts` antes de operar. La ausencia del complemento devuelve `TB_CLOSED`.

Para regenerar el paquete/registro: `pwsh -File scripts/install.ps1 -ProfilePath RUTA_DEL_PERFIL -AccountIds account1,account2`. El instalador conserva el ID existente y rechaza otra ruta de perfil. La lista de cuentas de este instalador corresponde a este equipo; para otros perfiles debe revisarse explícitamente en `runtime/config.json` y volver a empaquetar.

## Herramientas

Lectura: estado, cuentas/identidades, carpetas y contadores, búsqueda y continuación/cancelación, cuerpo MIME, cabeceras, adjuntos y EML por bloques, libretas/contactos, etiquetas y eventos. Las búsquedas reflejan el estado visible en Thunderbird; no garantizan un archivo completo del servidor. El cuerpo se limita a 100.000 caracteres, con indicador de truncado. Adjuntos/EML: máximo 25 MiB, bloques de 128 KiB.

Escritura: preparar borrador/respuesta/reenvío de texto, importación EML hasta 512 KiB, flags/etiquetas/junk, mover/copiar/archivar, papelera explícita y crear/renombrar/eliminar carpetas. Solo se eliminan carpetas normales vacías sin subcarpetas; se protegen carpetas especiales. Mover puede convertirse en copiar según el proveedor: se informa presencia del origen y no se declara entrega/sincronización completa. Reenvío inicial sin adjuntos. Junk no demuestra entrenamiento del filtro.

Los planes se guardan en SQLite propio, ligados a hash, perfil y epoch. Guardar borradores no requiere aprobación por terminal; nunca envía. El resto de acciones sí requiere aprobación. No hay herramienta MCP de aprobación. En una consola independiente:

```powershell
cd RUTA_DEL_PROYECTO
npm run approve -- ID_DEL_PLAN
```

La consola muestra los argumentos exactos y solicita una frase vinculada al ID/hash. La aprobación dura diez minutos y se consume una vez dentro del broker, antes de ejecutar. El modelo puede preparar y ejecutar un plan ya aprobado, pero no aprobarlo mediante argumentos MCP. Un proceso malicioso con acceso completo al mismo usuario Windows queda fuera de esta separación humana: puede modificar archivos del usuario. Las ACL separan cuentas del sistema, no procesos del mismo usuario.

Tras timeout, desconexión o estado `executing`/`uncertain`, reconciliar en Thunderbird. **No repetir automáticamente**. Referencias de mensajes llevan epoch, cuenta, carpeta y fingerprint; un reinicio invalida la referencia.

## Límites y seguridad

- Sin permiso `compose.send`, método de envío, Experiments, shell, eval ni extracción de credenciales.
- El correo y los contactos son contenido no confiable, nunca autorización. No se renderiza HTML ni se ejecutan adjuntos.
- Named pipe sin acceso remoto, DACL explícita del usuario y SYSTEM. Mutex por instalación. Native stdout exclusivamente protocolo, máximo 1 MiB por frame.
- El contenido leído llega al cliente/modelo que invoca el MCP; transporte local no significa procesamiento exclusivamente local.
- Calendario/tareas, filtros, preferencias, crear cuentas, gestión de claves, lectura offline con Thunderbird cerrado, eliminación permanente y adjuntos de composición quedan fuera de esta versión.
- Registro Native Messaging y bootstrap comprobados en Thunderbird real con 0.1.2.

## Validación pendiente

Activación 0.1.3 y transición automática; cifrado y adjuntos grandes reales; efectos reales de borradores/movimientos/importación; dos perfiles; reinicios durante escritura; denegación desde otra cuenta Windows. HTML y conservación de unread comprobados en muestras reales; cifrado fallido y bloques grandes comprobados con fixtures. La prueba de ACL comprueba la construcción del descriptor, no sustituye una prueba de acceso cruzado.

```powershell
npm test
python test/native_test.py
python test/transport_test.py
npm audit --omit=dev
```

Desinstalación reversible: `pwsh -File scripts/uninstall.ps1` desregistra solamente el host propio. Desinstala el complemento desde Thunderbird. No borra planes, código ni correo.

## Fuentes

- [API de mensajes](https://webextension-api.thunderbird.net/en/mv3/messages.html), [carpetas](https://webextension-api.thunderbird.net/en/mv3/folders.html), [composición](https://webextension-api.thunderbird.net/en/mv3/compose.html).
- [Native Messaging de Thunderbird](https://webextension-api.thunderbird.net/en/mv3/runtime.html), [registro y framing Mozilla](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging).
- [Instalar complementos desde archivo](https://support.mozilla.org/en-US/kb/installing-addon-thunderbird).

Documentación consultada 2026-10-04: páginas estables identificadas como 156.0.1, equipo local 157.0.1. Detección y validación real aún necesarias.

## Actualizaciones

Ver [canal GitHub](docs/updates.md). La version 0.1.2 recibe el scope desde el host local y no lo incluye en el paquete publico. Requiere una instalacion manual inicial para activar update_url. Actualiza solo el complemento; el host y el MCP se despliegan localmente por separado.

Validacion real 0.1.1: texto/HTML, unread, cabeceras y EML en cuatro cuentas; estado read preservado en las muestras. Activacion 0.1.2 verificada; transicion automatica pendiente.

Los contactos tienen scope independiente: addressBookIds en runtime/config.json. Sin lista explicita no se devuelven contactos/libretas. No se infiere propiedad de una libreta a partir de una cuenta IMAP.

## Diagnóstico y pruebas humanas

0.1.3 registra listeners de arranque de forma síncrona y usa alarms para recuperar conexiones tras suspensión del fondo MV3. El bootstrap expira a los diez segundos; las reconexiones reutilizan el backend mientras el scope no cambia. Preferencias del complemento permite consultar estado y reconectar. `get_diagnostics` devuelve estado vivo o códigos locales sin correo ni errores nativos sin filtrar.

El MCP puede registrarse con `codex mcp add thunderbird-local -- node RUTA_DEL_PROYECTO/src/server.js`. Se carga en una nueva sesión del cliente.

Para probar escrituras reversibles, ejecutar en una consola humana `node scripts/test-local-writes.js ID_CARPETA_PADRE_LOCAL`. Crea una carpeta de prueba vacía, la renombra y la elimina; cada paso muestra un plan exacto y exige aprobación independiente. No ejecutarlo mediante el agente. Si se interrumpe, revisar la carpeta de prueba antes de repetir. No prueba mensajes ni sincronización IMAP.
