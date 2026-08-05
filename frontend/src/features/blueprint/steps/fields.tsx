import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface FieldProps {
  label: string
  hint?: string
  children: React.ReactNode
}

export function Field({ label, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

interface NumberInputProps {
  value: number
  onChange: (v: number) => void
  placeholder?: string
  min?: number
  step?: number
}

export function NumberInput({ value, onChange, placeholder, min = 0, step }: NumberInputProps) {
  return (
    <Input
      type="number"
      min={min}
      step={step}
      placeholder={placeholder}
      value={Number.isFinite(value) ? value : ''}
      onChange={(e) => onChange(e.target.value === '' ? 0 : Number(e.target.value))}
    />
  )
}

interface SelectInputProps {
  value: string
  onChange: (v: string) => void
  options: string[]
  placeholder?: string
}

export function SelectInput({ value, onChange, options, placeholder }: SelectInputProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((opt) => (
          <SelectItem key={opt} value={opt}>
            {opt}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
