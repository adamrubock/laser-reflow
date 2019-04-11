
import React, { Component } from 'react'
import { Col, Button, Form } from 'react-bootstrap'


export default class OutputSelect extends Component {
	constructor(props) {
		super(props);
		this.state = {
			xDim: 0.0,
			yDim: 0.0,
			threshold: false,
			shutter: false,
			alignmentLaser: false,
			errorReset: false,
			formValidated: false,

		};
		this.handleInputChange = this.handleInputChange.bind(this);
		this.handleInputSubmit = this.handleInputSubmit.bind(this);
	}

	handleInputChange(event) {
		const target = event.target;
		const value = target.type === 'checkbox' ? target.checked : target.value;
		const id = target.id;
		this.setState({
			[id]: value
		});
	}

	handleInputSubmit(event) {
		event.preventDefault()
		const form = event.currentTarget;
		const isValid = form.checkValidity()
		this.setState({ formValidated: true });
		if (isValid === false) {
			event.stopPropogation();
			return;
		}
		const data = {
			x_width: this.state.xDim,
			y_width: this.state.yDim,
			threshold_digital: this.state.threshold,
			shutter_digital: this.state.shutter,
			alignment_laser_digital: this.state.alignmentLaser,
			reset_error_digital: this.state.errorReset
		}

		function postData(url =``, data = {}) {
			// Default options are marked with *
			return fetch(url, {
				method: "POST", 
				mode: "same-origin",
				cache: "no-cache",
				credentials: "same-origin",
				headers: {
					"Content-Type": "application/json",
				},
				redirect: "follow", // manual, *follow, error
				referrer: "no-referrer", // no-referrer, *client
				body: JSON.stringify(data), // body data type must match "Content-Type" header
			})
		}
		postData(`/ldm/control`,data)
			.then(response => console.log(JSON.stringify(response)))
			.catch(error => console.error(error));
	}

	render() {
		const { formValidated } = this.state;
		return (
			<Form style={{ "userSelect": "none" }} onChange={this.handleInputChange} onSubmit={this.handleInputSubmit} validated={formValidated}>
				<Form.Row>
					<Form.Group as={Col} controlId="xDim">
						<Form.Label>x-dim</Form.Label>
						<Form.Control type="number" min={0} max={1} step={0.01} />
					</Form.Group>
					<Form.Group as={Col} controlId="yDim">
						<Form.Label>y-dim</Form.Label>
						<Form.Control type="number" min={0} max={1} step={0.01} />
					</Form.Group>
				</Form.Row>
				<Form.Group>
					<Form.Check id="threshold" label="Threshold" />
					<Form.Check id="shutter" label="Shutter" />
					<Form.Check id="alignmentLaser" label="Alignment Laser" />
					<Form.Check id="errorReset" label="Error Reset" />
				</Form.Group>
				<Form.Group>
					<Button variant="primary" type="submit">Submit</Button>
				</Form.Group>
			</Form>
		)
	}
}
