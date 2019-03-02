import React from "react";
import ReactDOM from "react-dom";
import Container from "./components/Container";

const wrapper = document.getElementById("app");
wrapper ? ReactDOM.render(<Container/>, wrapper) : null;