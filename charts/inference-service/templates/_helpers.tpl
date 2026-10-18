{{- define "inference.name" -}}{{ .Chart.Name }}{{- end -}}

{{- define "inference.labels" -}}
app.kubernetes.io/name: {{ include "inference.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "inference.selectorLabels" -}}
app.kubernetes.io/name: {{ include "inference.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
