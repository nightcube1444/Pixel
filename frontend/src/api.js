import axios from "axios";

const OLD_API = "http://127.0.0.1:8000";
const MARKET_API = "http://127.0.0.1:5000";

export const getWatchlist = async () => {
  const res = await axios.get(`${OLD_API}/watchlist`);
  return res.data;
};

export const getCandles = async (ticker) => {
  const res = await axios.get(`${OLD_API}/candles/${ticker}`);
  return res.data;
};

export const getLiveTicker = async (ticker) => {
  const res = await axios.get(`${OLD_API}/live-ticker/${ticker}`);
  return res.data;
};

export const getMarketDashboard = async () => {
  const res = await axios.get(`${MARKET_API}/api/market/dashboard`);
  return res.data;
};

export const getLivePatterns = async () => {
  const res = await axios.get(`${MARKET_API}/api/market/live-patterns`);
  return res.data;
};

export const askMarketChat = async (question) => {
  const res = await axios.post(`${MARKET_API}/api/market/chat`, {
    question,
  });
  return res.data;
};
export const getSystemStatus = async () => {
  const res = await axios.get(`${OLD_API}/system-status`);
  return res.data;
};
export const getFileStatus = async () => {
  const res = await axios.get(`${OLD_API}/file-status`);
  return res.data;
};
export const getSystemHealth = async () => {
  const res = await axios.get(`${OLD_API}/system-health`);
  return res.data;
};
 