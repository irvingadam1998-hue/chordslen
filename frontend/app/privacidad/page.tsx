import { FileAudio, Mic, Server, Video } from 'lucide-react'
import PageHeading from '@/components/PageHeading'
export const metadata = { title: 'Privacidad — ChordLens' }
export default function PrivacidadPage() {
  return (
    <main className="shell py-12 sm:py-16">
      <PageHeading label="Privacidad" title="Qué ocurre con tu audio.">
        Información sobre el funcionamiento de esta versión y los servicios que
        intervienen.
      </PageHeading>
      <div className="panel max-w-3xl divide-y divide-[#dce2d8]">
        {[
          {
            icon: FileAudio,
            title: 'Archivos y análisis',
            text: 'Al subir un archivo, el audio se envía al backend para procesarlo. Los archivos de análisis se crean temporalmente y el flujo normal los elimina al terminar. Los resultados y estados de trabajos se guardan en una caché temporal para consultar el progreso y reutilizar análisis; su duración depende de la configuración del servidor.',
          },
          {
            icon: Video,
            title: 'YouTube y letras',
            text: 'Al analizar un enlace, el servidor solicita el audio a YouTube. El reproductor integrado establece conexiones con YouTube desde tu navegador. Si abres la letra, se consultan el título y el artista en el servicio de letras. Estos servicios tienen sus propias políticas de privacidad.',
          },
          {
            icon: Mic,
            title: 'Micrófono del afinador',
            text: 'El afinador solicita acceso al micrófono cuando lo activas. La detección de la nota se realiza en tu navegador. El código del afinador no envía esa señal al backend; al detenerlo se liberan las pistas del micrófono.',
          },
          {
            icon: Server,
            title: 'Infraestructura',
            text: 'Los proveedores que alojan la aplicación pueden registrar datos técnicos de las solicitudes. El uso normal de esta versión no requiere crear una cuenta. La configuración del alojamiento determina la conservación de logs y los accesos administrativos.',
          },
        ].map(({ icon: Icon, title, text }) => (
          <section key={title} className="flex items-start gap-4 p-6 sm:p-8">
            <Icon size={22} className="mt-1" />
            <div>
              <h2 className="mb-3 text-lg font-extrabold">{title}</h2>
              <p className="muted text-sm leading-7">{text}</p>
            </div>
          </section>
        ))}
      </div>
    </main>
  )
}
