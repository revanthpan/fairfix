import { useMemo, useState } from "react";
import { Calendar, DollarSign, Wrench } from "lucide-react";

type Mode = "quote" | "schedule" | null;

type Quote = {
  name: string;
  price: number;
  type: "Dealer" | "Indy";
  distance: number;
};

type ScheduleItem = {
  service_task: string;
  interval_miles: number;
  description: string;
  severity: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8002";
const SERVICE_OPTIONS = [
  "Brake Pad Replacement",
  "Oil Change",
  "Battery Replacement",
  "Tire Rotation",
  "Spark Plug Service",
];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

export default function App() {
  const [mode, setMode] = useState<Mode>(null);
  const [vehicle, setVehicle] = useState({
    year: "",
    make: "",
    model: "",
    mileage: "",
  });
  const [serviceName, setServiceName] = useState(SERVICE_OPTIONS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [schedule, setSchedule] = useState<ScheduleItem[] | null>(null);

  const dealers = useMemo(
    () => quotes?.filter((quote) => quote.type === "Dealer") ?? [],
    [quotes]
  );
  const indys = useMemo(
    () => quotes?.filter((quote) => quote.type === "Indy") ?? [],
    [quotes]
  );
  const dealerAverage = useMemo(() => {
    if (!dealers.length) {
      return 0;
    }
    const total = dealers.reduce((sum, quote) => sum + quote.price, 0);
    return Math.round(total / dealers.length);
  }, [dealers]);

  const handleModeChange = (nextMode: Mode) => {
    setMode(nextMode);
    setError(null);
    setQuotes(null);
    setSchedule(null);
  };

  const updateVehicle = (field: keyof typeof vehicle, value: string) => {
    setVehicle((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!mode) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (mode === "quote") {
        const params = new URLSearchParams({
          service_name: serviceName,
          make: vehicle.make.trim(),
          model: vehicle.model.trim(),
          year: vehicle.year.trim(),
        });
        const response = await fetch(`${API_BASE}/quotes?${params}`);
        if (!response.ok) {
          throw new Error("Unable to fetch quotes. Try again.");
        }
        const data = await response.json();
        setQuotes(data.quotes ?? []);
        setSchedule(null);
      } else {
        const params = new URLSearchParams({
          make: vehicle.make.trim(),
          model: vehicle.model.trim(),
          year: vehicle.year.trim(),
          mileage: vehicle.mileage.trim(),
        });
        const response = await fetch(`${API_BASE}/schedule?${params}`);
        if (!response.ok) {
          throw new Error("Unable to load schedule. Try again.");
        }
        const data = await response.json();
        setSchedule(data ?? []);
        setQuotes(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-10">
        <header className="flex flex-col gap-3">
          <p className="text-sm uppercase tracking-[0.3em] text-slate-400">
            FairFix Vehicle Maintenance
          </p>
          <h1 className="text-3xl font-semibold text-white sm:text-4xl">
            Choose your next move with clarity.
          </h1>
          <p className="max-w-2xl text-base text-slate-300">
            Get fast repair pricing intelligence or see what maintenance is due
            next. Start with a quick choice, then enter your vehicle details.
          </p>
        </header>

        <section className="grid gap-5 md:grid-cols-2">
          <button
            type="button"
            onClick={() => handleModeChange("quote")}
            className={`rounded-2xl border px-6 py-6 text-left transition ${
              mode === "quote"
                ? "border-emerald-400 bg-slate-900"
                : "border-slate-800 bg-slate-900/50 hover:border-slate-600"
            }`}
          >
            <div className="flex items-center gap-3 text-lg font-semibold">
              <DollarSign className="h-6 w-6 text-emerald-400" />
              💰 Get a Quote
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Compare dealership trust and independent savings on a specific
              service.
            </p>
          </button>
          <button
            type="button"
            onClick={() => handleModeChange("schedule")}
            className={`rounded-2xl border px-6 py-6 text-left transition ${
              mode === "schedule"
                ? "border-sky-400 bg-slate-900"
                : "border-slate-800 bg-slate-900/50 hover:border-slate-600"
            }`}
          >
            <div className="flex items-center gap-3 text-lg font-semibold">
              <Calendar className="h-6 w-6 text-sky-400" />
              📅 Maintenance Check
            </div>
            <p className="mt-2 text-sm text-slate-300">
              See what is due within the next 5,000 miles for your vehicle.
            </p>
          </button>
        </section>

        {mode && (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex items-center gap-3 text-lg font-semibold">
              <Wrench className="h-5 w-5 text-slate-300" />
              Vehicle Details
            </div>
            <form
              onSubmit={handleSubmit}
              className="mt-6 grid gap-4 md:grid-cols-2"
            >
              <label className="flex flex-col gap-2 text-sm text-slate-300">
                Year
                <input
                  required
                  type="number"
                  min={1900}
                  max={2100}
                  value={vehicle.year}
                  onChange={(event) => updateVehicle("year", event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-slate-300">
                Make
                <input
                  required
                  type="text"
                  value={vehicle.make}
                  onChange={(event) => updateVehicle("make", event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-slate-300">
                Model
                <input
                  required
                  type="text"
                  value={vehicle.model}
                  onChange={(event) => updateVehicle("model", event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-slate-300">
                Mileage
                <input
                  required
                  type="number"
                  min={0}
                  value={vehicle.mileage}
                  onChange={(event) =>
                    updateVehicle("mileage", event.target.value)
                  }
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                />
              </label>
              {mode === "quote" && (
                <label className="flex flex-col gap-2 text-sm text-slate-300 md:col-span-2">
                  Service
                  <select
                    value={serviceName}
                    onChange={(event) => setServiceName(event.target.value)}
                    className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                  >
                    {SERVICE_OPTIONS.map((service) => (
                      <option key={service} value={service}>
                        {service}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-emerald-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Loading..." : "Show Results"}
                </button>
              </div>
            </form>
            {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
          </section>
        )}

        {mode === "schedule" && schedule && (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex items-center gap-3 text-lg font-semibold">
              <Calendar className="h-5 w-5 text-sky-300" />
              Maintenance Checklist
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Due within the next 5,000 miles.
            </p>
            {schedule.length === 0 ? (
              <p className="mt-4 text-sm text-slate-400">
                No services due soon. You are on track.
              </p>
            ) : (
              <ul className="mt-5 space-y-4">
                {schedule.map((item) => (
                  <li
                    key={`${item.service_task}-${item.interval_miles}`}
                    className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-base font-semibold text-white">
                          Due Soon: {item.service_task}
                        </p>
                        <p className="text-xs text-slate-400">
                          {item.description}
                        </p>
                      </div>
                      <div className="text-right text-sm text-slate-300">
                        {item.interval_miles.toLocaleString()} mi
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {mode === "quote" && quotes && (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex items-center gap-3 text-lg font-semibold">
              <DollarSign className="h-5 w-5 text-emerald-300" />
              Quote Comparison
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Dealership trust vs. independent savings for {serviceName}.
            </p>
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <h3 className="text-base font-semibold text-white">
                  Dealership Quotes
                </h3>
                <p className="text-xs text-slate-400">
                  Authorized Dealer · High trust score
                </p>
                <div className="mt-4 space-y-4">
                  {dealers.map((quote) => (
                    <div
                      key={`${quote.name}-${quote.price}`}
                      className="flex items-center justify-between"
                    >
                      <div>
                        <p className="font-semibold">{quote.name}</p>
                        <p className="text-xs text-slate-400">
                          Authorized Dealer · {quote.distance} mi
                        </p>
                      </div>
                      <p className="text-lg font-semibold">
                        {formatCurrency(quote.price)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <h3 className="text-base font-semibold text-white">
                  Independent Shops
                </h3>
                <p className="text-xs text-slate-400">
                  Local Expert · Flexible pricing
                </p>
                <div className="mt-4 space-y-4">
                  {indys.map((quote) => {
                    const savings = Math.max(0, dealerAverage - quote.price);
                    return (
                      <div
                        key={`${quote.name}-${quote.price}`}
                        className="flex items-center justify-between"
                      >
                        <div>
                          <p className="font-semibold">{quote.name}</p>
                          <p className="text-xs text-slate-400">
                            Local Expert · {quote.distance} mi
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold">
                            {formatCurrency(quote.price)}
                          </p>
                          {savings > 0 && (
                            <p className="text-sm font-bold text-emerald-400">
                              Save {formatCurrency(savings)}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
