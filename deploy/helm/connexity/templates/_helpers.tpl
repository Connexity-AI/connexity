{{- define "connexity.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "connexity.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "connexity.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "connexity.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "connexity.labels" -}}
helm.sh/chart: {{ include "connexity.chart" . }}
app.kubernetes.io/name: {{ include "connexity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "connexity.selectorLabels" -}}
app.kubernetes.io/name: {{ include "connexity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "connexity.backend.selectorLabels" -}}
{{ include "connexity.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end -}}

{{- define "connexity.frontend.selectorLabels" -}}
{{ include "connexity.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end -}}

{{- define "connexity.mcp.selectorLabels" -}}
{{ include "connexity.selectorLabels" . }}
app.kubernetes.io/component: mcp
{{- end -}}

{{- define "connexity.voice.selectorLabels" -}}
{{ include "connexity.selectorLabels" . }}
app.kubernetes.io/component: voice-worker
{{- end -}}

{{- define "connexity.secretName" -}}
{{- if .Values.secret.create -}}
{{- include "connexity.fullname" . -}}
{{- else -}}
{{- .Values.secret.existingSecret -}}
{{- end -}}
{{- end -}}

{{- define "connexity.postgresql.fullname" -}}
{{- if .Values.postgresql.fullnameOverride -}}
{{- .Values.postgresql.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-postgresql" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "connexity.postgres.host" -}}
{{- if .Values.postgresql.enabled -}}
{{- include "connexity.postgresql.fullname" . -}}
{{- else -}}
{{- required "externalDatabase.host is required when postgresql.enabled=false" .Values.externalDatabase.host -}}
{{- end -}}
{{- end -}}

{{- define "connexity.postgres.port" -}}
{{- if .Values.postgresql.enabled -}}
5432
{{- else -}}
{{ .Values.externalDatabase.port }}
{{- end -}}
{{- end -}}

{{- define "connexity.postgres.user" -}}
{{- if .Values.postgresql.enabled -}}
{{ .Values.postgresql.auth.username }}
{{- else -}}
{{ .Values.externalDatabase.user }}
{{- end -}}
{{- end -}}

{{- define "connexity.postgres.password" -}}
{{- if .Values.postgresql.enabled -}}
{{ .Values.postgresql.auth.password }}
{{- else -}}
{{ .Values.externalDatabase.password }}
{{- end -}}
{{- end -}}

{{- define "connexity.postgres.database" -}}
{{- if .Values.postgresql.enabled -}}
{{ .Values.postgresql.auth.database }}
{{- else -}}
{{ .Values.externalDatabase.database }}
{{- end -}}
{{- end -}}

{{- define "connexity.backend.serviceName" -}}
{{- printf "%s-backend" (include "connexity.fullname" .) -}}
{{- end -}}

{{- define "connexity.frontend.serviceName" -}}
{{- printf "%s-frontend" (include "connexity.fullname" .) -}}
{{- end -}}

{{- define "connexity.mcp.serviceName" -}}
{{- printf "%s-mcp" (include "connexity.fullname" .) -}}
{{- end -}}

{{- define "connexity.voice.fullname" -}}
{{- printf "%s-voice-worker" (include "connexity.fullname" .) -}}
{{- end -}}

{{- define "connexity.backend.image" -}}
{{- $repo := .Values.backend.image.repository -}}
{{- $tag := .Values.backend.image.tag -}}
{{- if or .Values.backend.image.useVoiceVariant .Values.voice.enabled -}}
{{- $tag = .Values.backend.image.voiceTag -}}
{{- end -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}

{{- define "connexity.backend.apiUrl" -}}
{{- printf "http://%s:%v/api/v1" (include "connexity.backend.serviceName" .) .Values.backend.service.port -}}
{{- end -}}
