# Seguridad y privacidad

## Autenticación y sesiones
- Contraseñas con **scrypt** (sal por usuario); verificación en tiempo constante; mínimo 10 caracteres.
- Altas con **contraseña temporal** aleatoria y cambio obligatorio en el primer acceso; RRHH puede restablecer.
- Cookie de sesión `HttpOnly`, `SameSite=Lax`, `Secure` en producción, caducidad de 12 h; tokens aleatorios de 256 bits guardados en base.
- **Límite de intentos** de acceso por usuario y por IP (8 en 15 min → 429).

## CSRF y cabeceras
- Doble barrera: el middleware rechaza peticiones mutantes de origen cruzado (`Sec-Fetch-Site`/`Origin`) y cada formulario/API exige el token CSRF de la sesión (`csrf` o cabecera `X-CSRF`).
- Cabeceras: CSP (scripts sólo propios y cdnjs, estilos propios y Google Fonts, sin iframes), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS en producción.

## Roles y alcance
- `superadmin` (Mente Viva): plataforma, empresas, IA, presupuesto, bitácora; **no** consulta datos personales de colaboradores.
- `rrhh`: gestión y consulta de toda su empresa; único manager con acceso a transcripciones (trazado en bitácora al exportar).
- `dg`: consulta de toda la empresa (scores, feedback, planes) sin transcripciones.
- `director`: sólo su área; evalúa a sus colaboradores; sin transcripciones.
- `colaborador`: sólo lo propio. Las herramientas del Analista aplican el mismo alcance y nunca exponen transcripciones.

## Datos y IA
- La API key de Gemini vive únicamente en variables de entorno de Render; el nivel de pago de Google AI Studio evita el uso de datos para entrenamiento.
- A la IA sólo viaja lo necesario: instrucciones, perfil declarado, escenario, conversación de la sesión y, en el análisis, la transcripción de esa sesión. Los chats con managers reciben scores/feedback agregados, no diálogos.
- Prompts con reglas éticas: sin veredictos de empleabilidad, sin etiquetas de personalidad, reencuadre ante peticiones de manipulación, pausa ante malestar emocional real.
- **Presupuesto con tope duro**: ninguna llamada sale si el paquete mensual se agotó; búsquedas web acotadas por mes.
- Bitácora de accesos, seguridad, IA, aprobaciones y exportes en `/admin/bitacora`.

## Recomendaciones operativas
- Contraseñas temporales por canal seguro; desactivar cuentas al salir la persona (`/gestion`).
- Revisar mensualmente `/admin/uso` y `/admin/bitacora`.
- Respaldo del archivo SQLite (ver DESPLIEGUE.md).
- Antes de ampliar a más empresas: dominio propio con TLS (Render lo provee), política de retención de transcripciones y aviso de privacidad (LFPDPPP) para los colaboradores.
