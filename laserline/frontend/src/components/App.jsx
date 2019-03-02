import React, { Component } from "react";
import Table from "./Table";
import Form from "./Form";

class App extends Component {
	constructor(props) {
		super(props);
		this.state = {
			data:[],
			loaded: false,
			placeholder: "Loading..."
		};
		this.triggerUpdate=this.triggerUpdate.bind(this);
	}
	
	componentDidMount () {
		fetch("api/lead/")
			.then(response => {
				if (response.status !== 200) return this.setState({placeholder: "Something went wrong..."});
				return response.json();
			})
			.then(data => this.setState({ data: data, loaded: true}));
	}
	
	triggerUpdate () {
		this.setState({ loaded: false, placeholder: "Updating..." });
		fetch("api/lead/")
			.then(response => {
				if (response.status !== 200) {
					return this.setState({placeholder: "Something went wrong..."});
				}
				return response.json();
			})
			.then(data => this.setState({ data: data, loaded: true}));
	}

	render() {
		const {data, loaded, placeholder} = this.state;
		return (
			<React.Fragment>
				<Table data={data} loaded={loaded} placeholder={placeholder}/>
				<Form endpoint="api/lead/" triggerUpdate={this.triggerUpdate}/>
			</React.Fragment>
		)
	}
}

export default App;