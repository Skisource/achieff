function listenForBoardChanges(refresh) {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const connect = () => {
    const socket = new WebSocket(`${protocol}//${location.host}/live`);
    socket.onmessage = () => refresh();
    socket.onclose = () => window.setTimeout(connect, 2000);
  };
  connect();
}
