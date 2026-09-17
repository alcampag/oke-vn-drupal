{{- define "serverless-drupal.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "serverless-drupal.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "serverless-drupal.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "serverless-drupal.labels" -}}
helm.sh/chart: {{ include "serverless-drupal.chart" . }}
{{ include "serverless-drupal.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "serverless-drupal.selectorLabels" -}}
app.kubernetes.io/name: {{ include "serverless-drupal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "serverless-drupal.storageClassName" -}}
{{- default (printf "%s-fss-rwx" (include "serverless-drupal.fullname" .)) .Values.storage.storageClassName }}
{{- end }}
