class Slots:
    @staticmethod
    def slot_link():
        return """
        <q-td :props="props">
            <a :href="https://fr.tradingview.com/chart/?symbol=BINANCE:props.value">{0}</a>
        </q-td>
        """.format("{{ props.value }}")

    @staticmethod
    def slot_red_green(col_name: str, symbol: str = "%", condition: str = "props.value < 0 ? 'red':'green'"):
        return """
        <q-td align="middle">
            <q-badge key="{0}" :props="props" outline  :color="{1}">
                {2} {3}
            </q-badge>
        </q-td>
        """.format(col_name, condition, "{{props.value.toFixed(2)}}", symbol)

    @staticmethod
    def slot_timestamp(col_name: str):
        return """
        <q-td align="middle">
            <q-badge key="{0}" :props="props" outline>
                {1}
            </q-badge>
        </q-td>
        """.format(col_name, "{{typeof(props.value)}}")
