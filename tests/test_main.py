from notifrw.main import SeatClass, TrainInfo, parse_trains


FIXTURE_HTML = """
<div class="sch-table__row-wrap js-row w_places">
  <div class="sch-table__row" data-train-number="689Б">
    <div class="sch-table__cell cell-1">
      <a class="sch-table__route">
        <span class="train-number">689Б</span>
      </a>
    </div>
    <div class="sch-table__cell cell-2">
      <div class="sch-table__time train-from-time">19:37</div>
      <div class="sch-table__time train-to-time">00:13</div>
    </div>
    <div class="sch-table__cell cell-3">
      <div class="sch-table__duration train-duration-time">4 ч 36 мин</div>
    </div>
    <div class="sch-table__cell cell-4">
      <div class="sch-table__tickets">
        <div class="sch-table__t-item has-quant">
          <div class="sch-table__t-name">Плацкартный</div>
          <a class="sch-table__t-quant"><span>148</span></a>
          <div class="sch-table__t-cost">
            <div class="ticket-wrap">
              <span class="js-price" data-cost-byn="17,20">
                <span class="ticket-cost">17,20</span>
              </span>
            </div>
          </div>
        </div>
        <div class="sch-table__t-item has-quant">
          <div class="sch-table__t-name">Купейный</div>
          <a class="sch-table__t-quant"><span>53</span></a>
          <div class="sch-table__t-cost">
            <div class="ticket-wrap">
              <span class="js-price" data-cost-byn="23,82">
                <span class="ticket-cost">23,82</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="sch-table__row-wrap js-row">
  <div class="sch-table__row" data-train-number="707Б">
    <div class="sch-table__cell cell-1">
      <a class="sch-table__route">
        <span class="train-number">707Б</span>
      </a>
    </div>
    <div class="sch-table__cell cell-2">
      <div class="sch-table__time train-from-time">07:00</div>
      <div class="sch-table__time train-to-time">09:50</div>
    </div>
    <div class="sch-table__cell cell-3">
      <div class="sch-table__duration train-duration-time">2 ч 50 мин</div>
    </div>
    <div class="sch-table__cell cell-4 empty">
      <div class="sch-table__tickets"></div>
      <div class="sch-table__no-info">Мест нет</div>
    </div>
  </div>
</div>

<div class="sch-table__row-wrap js-row w_places">
  <div class="sch-table__row" data-train-number="755Б">
    <div class="sch-table__cell cell-1">
      <a class="sch-table__route">
        <span class="train-number">755Б</span>
      </a>
    </div>
    <div class="sch-table__cell cell-2">
      <div class="sch-table__time train-from-time">04:41</div>
      <div class="sch-table__time train-to-time">07:53</div>
    </div>
    <div class="sch-table__cell cell-3">
      <div class="sch-table__duration train-duration-time">3 ч 12 мин</div>
    </div>
    <div class="sch-table__cell cell-4">
      <div class="sch-table__tickets">
        <div class="sch-table__t-item has-quant">
          <div class="sch-table__t-name">Сидячий</div>
          <a class="sch-table__t-quant"><span>66</span></a>
          <div class="sch-table__t-cost">
            <div class="ticket-wrap">
              <span class="js-price" data-cost-byn="14,06">
                <span class="ticket-cost">14,06</span>
              </span>
            </div>
            <div class="ticket-wrap">
              <span class="js-price" data-cost-byn="20,08">
                <span class="ticket-cost">20,08</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


class TestParseTrains:
    def test_parses_train_with_seats(self):
        trains = parse_trains(FIXTURE_HTML)
        train = next(t for t in trains if t.number == "689Б")
        assert train.departure == "19:37"
        assert train.arrival == "00:13"
        assert train.duration == "4 ч 36 мин"
        assert len(train.seats) == 2
        assert train.seats[0] == SeatClass(
            name="Плацкартный", count=148, price_byn="17,20"
        )
        assert train.seats[1] == SeatClass(
            name="Купейный", count=53, price_byn="23,82"
        )

    def test_skips_train_without_seats(self):
        trains = parse_trains(FIXTURE_HTML)
        numbers = {t.number for t in trains}
        assert "707Б" not in numbers

    def test_returns_only_trains_with_seats(self):
        trains = parse_trains(FIXTURE_HTML)
        assert len(trains) == 2
        assert {t.number for t in trains} == {"689Б", "755Б"}

    def test_filters_by_train_numbers(self):
        trains = parse_trains(FIXTURE_HTML, train_filter={"689Б"})
        assert len(trains) == 1
        assert trains[0].number == "689Б"

    def test_multiple_price_tiers_uses_lowest(self):
        trains = parse_trains(FIXTURE_HTML)
        train = next(t for t in trains if t.number == "755Б")
        assert train.seats[0].price_byn == "14,06"
