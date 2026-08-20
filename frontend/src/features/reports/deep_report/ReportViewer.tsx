interface Props {
  pdfUrl: string
}

export function ReportViewer({ pdfUrl }: Props) {
  return (
    <div
      className="rounded-lg overflow-hidden border border-slate-700"
      style={{ height: '70vh' }}
    >
      <iframe
        src={pdfUrl}
        className="w-full h-full"
        title="Deep-Dive Report"
      />
    </div>
  )
}
