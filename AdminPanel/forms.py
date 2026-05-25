from django import forms

from TurnosMed.models import Area, ProgramacionVacaciones, Sala, Usuario

class UsuarioForm(forms.ModelForm):
    class Meta:
        model  = Usuario
        fields = [
            'nombre', 'apellidos', 'telefono', 'dni', 'email',
            'fecha_nacimiento', 'fecha_ingreso',
            'rol', 'tipo_trabajador', 'condicion',
            'departamento', 'area', 'sala', 'is_active',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre(s)',
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellidos',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ej. 999888777',
                'maxlength': '9',
            }),
            'dni': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ej. 77889911',
                'maxlength': '8',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ej. napellido@hep.pe',
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_ingreso': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'rol': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_rol',
            }),
            'tipo_trabajador': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_tipo_trabajador',
            }),
            'condicion': forms.Select(attrs={
                'class': 'form-control',
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_departamento',
            }),
            'area': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_area',
            }),
            'sala': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_sala',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Área y sala empiezan vacíos
        self.fields['area'].queryset = Area.objects.none()
        self.fields['sala'].queryset = Sala.objects.none()

        # Si es edición, cargar las opciones del área y sala actuales
        if self.instance.pk:
            if self.instance.departamento_id:
                self.fields['area'].queryset = Area.objects.filter(
                    departamento=self.instance.departamento,
                    activo=True,
                ).order_by('nombre')
            if self.instance.area_id:
                self.fields['sala'].queryset = Sala.objects.filter(
                    area=self.instance.area,
                    activa=True,
                ).order_by('nombre')

        # Si el POST trajo datos, cargar las opciones según lo enviado
        if 'departamento' in self.data:
            try:
                dep_id = int(self.data.get('departamento'))
                self.fields['area'].queryset = Area.objects.filter(
                    departamento_id=dep_id,
                    activo=True,
                ).order_by('nombre')
            except (ValueError, TypeError):
                pass

        if 'area' in self.data:
            try:
                area_id = int(self.data.get('area'))
                self.fields['sala'].queryset = Sala.objects.filter(
                    area_id=area_id,
                    activa=True,
                ).order_by('nombre')
            except (ValueError, TypeError):
                pass

        # Campos no obligatorios a nivel de form
        self.fields['telefono'].required  = False
        self.fields['fecha_nacimiento'].required = False
        self.fields['fecha_ingreso'].required = False
        self.fields['tipo_trabajador'].required = False
        self.fields['condicion'].required = False
        self.fields['departamento'].required = False
        self.fields['area'].required = False
        self.fields['sala'].required = False
        self.fields['is_active'].required = False

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono and len(telefono) != 9:
            raise forms.ValidationError('El teléfono debe tener exactamente 9 dígitos.')
        if telefono and not telefono.isdigit():
            raise forms.ValidationError('El teléfono solo debe contener números.')
        return telefono

    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').strip()
        if not dni:
            raise forms.ValidationError('El DNI es obligatorio.')
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener exactamente 8 dígitos.')
        if not dni.isdigit():
            raise forms.ValidationError('El DNI solo debe contener números.')
        return dni


class ProgramacionVacacionesForm(forms.ModelForm):
    class Meta:
        model = ProgramacionVacaciones
        fields = ['trabajador', 'anio', 'fecha_inicio', 'fecha_fin', 'observaciones']
        labels = {'anio': 'Año'}
        widgets = {
            'trabajador': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones opcionales',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trabajador'].queryset = Usuario.objects.filter(
            rol__in=['jefe_area', 'asistencial'],
            is_active=True,
        ).select_related('departamento', 'area').order_by('apellidos', 'nombre')
