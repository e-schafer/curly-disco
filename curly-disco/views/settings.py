import models
from nicegui import events, ui


class SettingsView:
    async def update_settings(self, e: events.GenericEventArguments):
        ui.notify("Updating settings...")
        if setting := await models.Settings.get_or_none(key=e.args["key"]):
            setting.value = e.args["value"]
            await setting.save()
            ui.notify("Settings updated!")

    async def render(self):
        with ui.table(
            rows=await models.Settings.all().values(), columns=models.Settings.nicegui_repr()
        ) as settings_table:
            settings_table.add_slot(
                "body-cell-value",
                """
                    <q-td key="value" :props="props">
                    {{ props.row.value }}
                    <q-popup-edit v-model="props.row.value" v-slot="scope"  @update:model-value="() => $parent.$emit('update', props.row)">
                    <q-input v-model.number="scope.value" type="number"  dense autofocus counter @keyup.enter="scope.set" />
                    </q-popup-edit>
                    </q-td>""",
            )
            settings_table.on("update", self.update_settings)
