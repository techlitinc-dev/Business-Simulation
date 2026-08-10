import { useEffect, useState } from 'react'

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

/**
 * Number input that keeps a local string state so users can clear the field
 * and type a fresh value — the old behavior coerced '' to 0 on every change,
 * which made intermediate typing impossible.
 */
export function NumberInput({ value, onChange, placeholder, min = 0, step }: NumberInputProps) {
  const [text, setText] = useState<string>(Number.isFinite(value) ? String(value) : '')

  useEffect(() => {
    setText(Number.isFinite(value) ? String(value) : '')
  }, [value])

  return (
    <Input
      type="number"
      min={min}
      step={step}
      placeholder={placeholder}
      value={text}
      onChange={(e) => {
        const raw = e.target.value
        setText(raw)
        if (raw !== '' && Number.isFinite(Number(raw))) {
          onChange(Number(raw))
        }
      }}
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
