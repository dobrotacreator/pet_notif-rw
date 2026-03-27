from notifrw.main import (
    SeatClass,
    TrainInfo,
    filter_new_trains,
    parse_trains,
    parse_watch_url,
)


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


class TestParseWatchUrl:
    def test_valid_url_with_all_params(self):
        url = (
            "https://pass.rw.by/ru/route/"
            "?from=Гомель&from_exp=2100100&to=Минск&to_exp=2100000"
            "&date=2026-03-29&front_date=29+мар.+2026"
        )
        result = parse_watch_url(url)
        assert result == {
            "url": url,
            "from": "Гомель",
            "to": "Минск",
            "date": "2026-03-29",
        }

    def test_invalid_host_returns_none(self):
        assert parse_watch_url("https://example.com/route?from=A&to=B") is None

    def test_missing_from_returns_none(self):
        assert parse_watch_url("https://pass.rw.by/ru/route/?to=Минск") is None

    def test_missing_to_returns_none(self):
        assert parse_watch_url("https://pass.rw.by/ru/route/?from=Гомель") is None

    def test_garbage_string_returns_none(self):
        assert parse_watch_url("not a url") is None


class TestFilterNewTrains:
    def test_first_check_all_trains_are_new(self):
        trains = [
            TrainInfo("689Б", "19:37", "00:13", "4 ч", []),
            TrainInfo("755Б", "04:41", "07:53", "3 ч", []),
        ]
        new, notified = filter_new_trains(trains, set())
        assert len(new) == 2
        assert notified == {"689Б", "755Б"}

    def test_already_notified_trains_skipped(self):
        trains = [TrainInfo("689Б", "19:37", "00:13", "4 ч", [])]
        new, notified = filter_new_trains(trains, {"689Б"})
        assert len(new) == 0
        assert notified == {"689Б"}

    def test_disappeared_train_removed_from_notified(self):
        new, notified = filter_new_trains([], {"689Б"})
        assert len(new) == 0
        assert notified == set()

    def test_reappeared_train_notified_again(self):
        _, notified = filter_new_trains([], {"689Б"})
        assert notified == set()
        trains = [TrainInfo("689Б", "19:37", "00:13", "4 ч", [])]
        new, notified = filter_new_trains(trains, notified)
        assert len(new) == 1
        assert new[0].number == "689Б"
        assert notified == {"689Б"}

    def test_mix_of_new_and_existing(self):
        trains = [
            TrainInfo("689Б", "19:37", "00:13", "4 ч", []),
            TrainInfo("755Б", "04:41", "07:53", "3 ч", []),
        ]
        new, notified = filter_new_trains(trains, {"689Б"})
        assert len(new) == 1
        assert new[0].number == "755Б"
        assert notified == {"689Б", "755Б"}
