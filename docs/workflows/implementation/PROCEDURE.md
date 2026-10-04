# Procedimiento de implementación y activación

1. Revisar versión, perfil seleccionado y cuentas sin leer secretos. Inventariar cambios y preservar otros complementos.
2. Contrastar API pública y permisos; no introducir Experiments o envío en el núcleo inicial.
3. Regenerar instalación con ID estable, ACL, manifiesto y XPI. No alterar prefs, key4.db, logins.json, mbox, msf ni SQLite de Thunderbird.
4. Ejecutar pruebas Node/Python, transporte Windows y audit. Documentar fallos y correcciones.
5. Activar XPI desde el gestor de complementos, registrar cliente stdio y comprobar estado/cuentas.
6. Verificar lectura de mensajes de prueba por cuenta, paginación, unread, MIME y adjuntos; redactar y ejecutar solo planes aprobados en consola independiente.
7. Probar reconexión, clientes concurrentes, referencias obsoletas, scopes y acceso cruzado Windows. Reconciliar escrituras inciertas; no replay.
8. Informar por separado implementación, instalación, validación sintética y validación real. Desregistrar con uninstall.ps1 para rollback; conservar datos propios.
