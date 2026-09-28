export default function PageHeading({
  label,
  title,
  children,
}: {
  label: string
  title: string
  children: React.ReactNode
}) {
  return (
    <header className="page-heading">
      <p className="eyebrow">{label}</p>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  )
}
