import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Política de Privacidad — ChordLens',
  description:
    'Política de privacidad de ChordLens. Información sobre qué datos recopilamos, cómo los usamos y tus derechos.',
}

const sections = [
  {
    id: 'informacion',
    title: '1. Información que recopilamos',
    content: [
      {
        subtitle: 'Información que no recopilamos',
        text: 'ChordLens no almacena las URLs de YouTube que ingresás, no guarda los resultados de los análisis, no crea perfiles de usuario y no rastrea tu historial de canciones analizadas. Cada análisis es procesado en tiempo real y descartado inmediatamente al finalizar la sesión.',
      },
      {
        subtitle: 'Datos de uso anónimos',
        text: 'Podemos recopilar datos de uso completamente anónimos a través de herramientas de analítica web, como el número de análisis realizados por día, los países de origen de las visitas y los navegadores más utilizados. Estos datos no contienen información personal identificable y se usan únicamente para mejorar el servicio.',
      },
      {
        subtitle: 'Datos de contacto',
        text: 'Si nos contactás por correo electrónico, almacenamos tu dirección de email y el contenido de la comunicación exclusivamente para responder tu consulta. No lo compartimos con terceros ni lo usamos para fines comerciales.',
      },
    ],
  },
  {
    id: 'uso',
    title: '2. Cómo usamos la información',
    content: [
      {
        subtitle: 'Prestación del servicio',
        text: 'La URL de YouTube que ingresás es utilizada exclusivamente para descargar el audio, analizarlo y devolverte los acordes. Este proceso ocurre en el servidor y el audio descargado es eliminado automáticamente al finalizar el análisis. No guardamos copias del audio ni de los resultados.',
      },
      {
        subtitle: 'Mejora del producto',
        text: 'Los datos de uso anónimos nos ayudan a entender cómo se usa ChordLens, qué funciones son más populares y dónde hay oportunidades de mejora. Nunca tomamos decisiones basadas en información personal.',
      },
      {
        subtitle: 'Comunicaciones',
        text: 'Si te suscribís a nuestro newsletter, usamos tu email únicamente para enviarte los contenidos de ChordLens (artículos del blog, novedades del producto). Podés cancelar la suscripción en cualquier momento haciendo clic en el enlace de baja incluido en cada email.',
      },
    ],
  },
  {
    id: 'cookies',
    title: '3. Cookies',
    content: [
      {
        subtitle: 'Cookies técnicas',
        text: 'ChordLens utiliza cookies técnicas estrictamente necesarias para el funcionamiento de la aplicación. Estas cookies no contienen información personal y son eliminadas al cerrar el navegador. No podés desactivarlas sin afectar el funcionamiento del sitio.',
      },
      {
        subtitle: 'Cookies de analítica',
        text: 'Podemos utilizar cookies de analítica de forma anónima para medir el tráfico del sitio. Si preferís no recibir estas cookies, podés configurar tu navegador para rechazarlas. El sitio seguirá funcionando con normalidad.',
      },
      {
        subtitle: 'Sin cookies de publicidad',
        text: 'ChordLens no utiliza cookies de seguimiento publicitario, no participa en redes de publicidad programática y no comparte datos de comportamiento con plataformas de publicidad.',
      },
    ],
  },
  {
    id: 'terceros',
    title: '4. Servicios de terceros',
    content: [
      {
        subtitle: 'YouTube (Google LLC)',
        text: 'ChordLens utiliza yt-dlp para descargar audio de videos de YouTube. Al ingresar una URL de YouTube, tu solicitud pasa a través de los servidores de YouTube/Google. El uso de YouTube está sujeto a las Políticas de Privacidad y Términos de Servicio de Google. ChordLens opera de acuerdo con los términos de uso de la API de YouTube.',
      },
      {
        subtitle: 'lyrics.ovh',
        text: 'Para obtener la letra de las canciones, ChordLens puede consultar la API pública de lyrics.ovh. Esta consulta incluye el nombre del artista y el título de la canción. No incluye ningún dato personal del usuario.',
      },
      {
        subtitle: 'Servicios de hosting',
        text: 'ChordLens está alojado en servicios de infraestructura cloud. Estos proveedores pueden tener acceso a los logs del servidor según sus propias políticas de privacidad, pero no tienen acceso a datos personales de usuarios de ChordLens.',
      },
    ],
  },
  {
    id: 'seguridad',
    title: '5. Seguridad',
    content: [
      {
        subtitle: 'Medidas técnicas',
        text: 'ChordLens utiliza conexiones HTTPS para todo el tráfico entre tu navegador y nuestros servidores. El audio descargado para el análisis se almacena temporalmente en un sistema de archivos con acceso restringido y es eliminado automáticamente al finalizar el proceso.',
      },
      {
        subtitle: 'Limitaciones',
        text: 'Ningún sistema de seguridad es infalible. Si bien implementamos prácticas recomendadas de seguridad, no podemos garantizar la seguridad absoluta de la información transmitida a través de Internet. Te recomendamos no ingresar URLs de videos con contenido privado o confidencial.',
      },
    ],
  },
  {
    id: 'cambios',
    title: '6. Cambios en esta política',
    content: [
      {
        subtitle: 'Notificación de cambios',
        text: 'Podemos actualizar esta política de privacidad periódicamente para reflejar cambios en nuestras prácticas o en la legislación aplicable. La fecha de la última actualización siempre estará visible al inicio de este documento. Para cambios significativos, notificaremos a los usuarios suscritos a nuestro newsletter.',
      },
      {
        subtitle: 'Continuidad del servicio',
        text: 'El uso continuado de ChordLens después de la publicación de cambios en esta política implica tu aceptación de dichos cambios. Si no estás de acuerdo con los cambios, podés dejar de usar el servicio.',
      },
    ],
  },
  {
    id: 'contacto',
    title: '7. Contacto',
    content: [
      {
        subtitle: 'Consultas sobre privacidad',
        text: 'Si tenés preguntas, inquietudes o solicitudes relacionadas con tu privacidad y el tratamiento de tus datos, podés contactarnos en: privacidad@chordlens.app. Respondemos todas las consultas en un plazo máximo de 30 días hábiles.',
      },
      {
        subtitle: 'Derechos del usuario',
        text: 'Tenés derecho a solicitar acceso, rectificación o eliminación de cualquier dato personal que tengamos sobre vos. Dado que ChordLens no almacena datos personales identificables en el uso normal del servicio, en la mayoría de los casos no habrá datos que rectificar o eliminar.',
      },
    ],
  },
]

export default function PrivacidadPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <section className="border-b border-white/5 py-14 px-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-3">
          <p className="text-yellow-400 text-xs font-mono tracking-widest">LEGAL</p>
          <h1 className="text-4xl font-black tracking-tighter">Política de Privacidad</h1>
          <p className="text-white/40 text-sm">
            Última actualización: <span className="text-white/60">15 de marzo, 2025</span>
          </p>
          <div className="mt-2 bg-yellow-400/8 border border-yellow-400/15 rounded-xl px-4 py-3">
            <p className="text-yellow-400/80 text-sm leading-relaxed">
              <strong className="text-yellow-400">Resumen:</strong> ChordLens no almacena tus URLs ni
              tus análisis. No recopilamos datos personales. El audio se procesa en tiempo real y se
              descarta inmediatamente.
            </p>
          </div>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-14 flex flex-col gap-12">

        {/* Intro */}
        <p className="text-white/50 text-sm leading-relaxed">
          En ChordLens respetamos tu privacidad y nos comprometemos a protegerla. Esta política
          describe qué información recopilamos cuando usás ChordLens, cómo la usamos y cuáles son
          tus derechos. Al usar ChordLens, aceptás las prácticas descritas en este documento.
        </p>

        {/* Sections */}
        {sections.map((section) => (
          <section key={section.id} className="flex flex-col gap-6">
            <h2 className="text-xl font-bold text-white border-b border-white/8 pb-3">
              {section.title}
            </h2>
            <div className="flex flex-col gap-5">
              {section.content.map(({ subtitle, text }) => (
                <div key={subtitle} className="flex flex-col gap-2">
                  <h3 className="text-sm font-semibold text-white/80">{subtitle}</h3>
                  <p className="text-white/45 text-sm leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </section>
        ))}

        {/* Footer note */}
        <div className="border-t border-white/5 pt-8 text-center">
          <p className="text-white/25 text-xs leading-relaxed">
            Esta política de privacidad aplica exclusivamente al servicio ChordLens disponible en
            chordlens.app. Para consultas legales, escribí a{' '}
            <a href="mailto:legal@chordlens.app" className="text-white/40 hover:text-white/60 underline">
              legal@chordlens.app
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  )
}
